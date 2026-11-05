from fastapi import HTTPException
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session
from app.documents.models import Assignment, Course, Document, Enrollment, Version
from app.models import Membership

PRIVILEGED = {"superadmin", "admin", "coordinator", "auditor"}
MANAGERS = {"superadmin", "admin", "coordinator"}


def visible(member: Membership):
    if member.role in PRIVILEGED:
        return Document.institution_id == member.institution_id
    course_access = exists(
        select(Assignment.id)
        .join(Course)
        .where(
            Assignment.id == Document.assignment_id,
            Course.teacher_id == member.id,
            Assignment.institution_id == member.institution_id,
        )
    )
    return and_(
        Document.institution_id == member.institution_id,
        or_(Document.owner_id == member.id, course_access if member.role == "teacher" else False),
    )


def get_document(db: Session, member: Membership, document_id: str, *, lock: bool = False) -> tuple[Document, Version]:
    query = select(Document).where(Document.id == document_id, Document.deleted_at.is_(None), visible(member))
    if lock:
        query = query.with_for_update()
    document = db.scalar(query)
    if document is None:
        raise HTTPException(404, "Documento no disponible")
    version = db.scalar(
        select(Version).where(Version.document_id == document.id, Version.institution_id == member.institution_id)
    )
    if version is None:
        raise HTTPException(404, "Versión no disponible")
    return document, version


def validate_association(db: Session, member: Membership, assignment_id: str | None, owner_id: str | None) -> str:
    owner_id = owner_id or member.id
    if member.role == "auditor":
        raise HTTPException(403, "El rol auditor es de solo lectura")
    if owner_id != member.id:
        owner = db.scalar(
            select(Membership).where(
                Membership.id == owner_id,
                Membership.institution_id == member.institution_id,
                Membership.role == "student",
                Membership.active.is_(True),
            )
        )
        if owner is None or member.role not in MANAGERS | {"teacher"} or not assignment_id:
            raise HTTPException(403, "No puedes cargar en nombre de ese estudiante")
    if assignment_id:
        row = db.execute(
            select(Assignment, Course)
            .join(Course)
            .where(Assignment.id == assignment_id, Assignment.institution_id == member.institution_id)
        ).first()
        if row is None:
            raise HTTPException(404, "Actividad no disponible")
        assignment, course = row
        if member.role not in MANAGERS and member.role != "student" and course.teacher_id != member.id:
            raise HTTPException(403, "No tienes acceso a esta asignatura")
        if member.role == "student" or owner_id != member.id:
            enrolled = db.scalar(
                select(Enrollment.id).where(
                    Enrollment.course_id == course.id,
                    Enrollment.student_id == owner_id,
                    Enrollment.institution_id == member.institution_id,
                )
            )
            if not enrolled:
                raise HTTPException(403, "El estudiante no está matriculado en la asignatura")
    return owner_id
