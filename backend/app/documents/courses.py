from uuid import UUID
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.auth import DB, Member
from app.documents.models import Assignment, Course, Enrollment
from app.documents.service import MANAGERS
from app.models import Membership

router = APIRouter(prefix="/api/v1", tags=["Asignaturas y actividades"])


class CourseInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    teacher_id: UUID | None = None


class AssignmentInput(BaseModel):
    course_id: UUID
    name: str = Field(min_length=1, max_length=160)


class EnrollmentInput(BaseModel):
    student_id: UUID


def course_access(member):
    if member.role in MANAGERS | {"auditor"}:
        return Course.institution_id == member.institution_id
    if member.role == "teacher":
        return Course.teacher_id == member.id
    return Course.id.in_(
        select(Enrollment.course_id).where(
            Enrollment.student_id == member.id, Enrollment.institution_id == member.institution_id
        )
    )


def managed_course(db, member, id):
    course = db.scalar(select(Course).where(Course.id == str(id), Course.institution_id == member.institution_id))
    if course is None:
        raise HTTPException(404, "Asignatura no disponible")
    if member.role not in MANAGERS and not (member.role == "teacher" and course.teacher_id == member.id):
        raise HTTPException(403, "No puedes gestionar esta asignatura")
    return course


@router.get("/courses")
def courses(member: Member, db: DB) -> dict:
    return {
        "items": [
            {"id": c.id, "name": c.name, "teacher_id": c.teacher_id}
            for c in db.scalars(select(Course).where(course_access(member)).order_by(Course.name).limit(100))
        ]
    }


@router.post("/courses", status_code=201)
def create_course(body: CourseInput, member: Member, db: DB) -> dict:
    if member.role not in MANAGERS | {"teacher"}:
        raise HTTPException(403, "No puedes crear asignaturas")
    teacher_id = str(body.teacher_id) if body.teacher_id else member.id
    if teacher_id != member.id and member.role not in MANAGERS:
        raise HTTPException(403, "No puedes asignar otro docente")
    teacher = db.scalar(
        select(Membership).where(
            Membership.id == teacher_id, Membership.institution_id == member.institution_id, Membership.active.is_(True)
        )
    )
    if teacher is None or teacher.role not in MANAGERS | {"teacher"}:
        raise HTTPException(422, "Docente no válido")
    course = Course(institution_id=member.institution_id, teacher_id=teacher_id, name=body.name)
    db.add(course)
    db.flush()
    return {"id": course.id, "name": course.name}


@router.get("/assignments")
def assignments(member: Member, db: DB) -> dict:
    rows = db.execute(
        select(Assignment, Course).join(Course).where(course_access(member)).order_by(Assignment.name).limit(100)
    )
    return {"items": [{"id": a.id, "name": a.name, "course_id": c.id, "course": c.name} for a, c in rows]}


@router.post("/assignments", status_code=201)
def create_assignment(body: AssignmentInput, member: Member, db: DB) -> dict:
    course = managed_course(db, member, body.course_id)
    assignment = Assignment(institution_id=member.institution_id, course_id=course.id, name=body.name)
    db.add(assignment)
    db.flush()
    return {"id": assignment.id, "name": assignment.name}


@router.post("/courses/{course_id}/enrollments", status_code=201)
def enroll(course_id: UUID, body: EnrollmentInput, member: Member, db: DB) -> dict:
    course = managed_course(db, member, course_id)
    student = db.scalar(
        select(Membership).where(
            Membership.id == str(body.student_id),
            Membership.institution_id == member.institution_id,
            Membership.active.is_(True),
            Membership.role == "student",
        )
    )
    if student is None:
        raise HTTPException(422, "Estudiante no válido")
    db.add(Enrollment(institution_id=member.institution_id, course_id=course.id, student_id=student.id))
    db.flush()
    return {"message": "Matrícula registrada"}


@router.get("/courses/{course_id}/students")
def students(course_id: UUID, member: Member, db: DB) -> dict:
    from app.models import User

    course = managed_course(db, member, course_id)
    enrolled = set(db.scalars(select(Enrollment.student_id).where(Enrollment.course_id == course.id)))
    rows = db.execute(
        select(Membership, User)
        .join(User)
        .where(
            Membership.institution_id == member.institution_id,
            Membership.active.is_(True),
            Membership.role == "student",
        )
        .order_by(User.name)
        .limit(100)
    )
    return {"items": [{"id": m.id, "name": u.name, "enrolled": m.id in enrolled} for m, u in rows]}


@router.get("/course-teachers")
def teachers(member: Member, db: DB) -> dict:
    from app.models import User

    if member.role not in MANAGERS | {"teacher"}:
        raise HTTPException(403, "No tienes permiso para consultar docentes")
    rows = db.execute(
        select(Membership, User)
        .join(User)
        .where(
            Membership.institution_id == member.institution_id,
            Membership.active.is_(True),
            Membership.role.in_(["teacher", "admin", "coordinator", "superadmin"]),
        )
        .order_by(User.name)
        .limit(100)
    )
    return {"items": [{"id": m.id, "name": u.name} for m, u in rows]}
