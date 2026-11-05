"""Provisionamiento local; ejecutar con DATABASE_URL del rol migrador."""

import argparse
import getpass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import engine
from app.models import Institution, Membership, User
from app.security import hasher


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--institution", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=["admin", "superadmin"], default="admin")
    args = parser.parse_args()
    from email_validator import validate_email

    email = validate_email(args.email, check_deliverability=False).normalized.lower()
    password = getpass.getpass("Contraseña inicial (mínimo 12 caracteres): ")
    if not 12 <= len(password) <= 256:
        parser.error("La contraseña debe tener entre 12 y 256 caracteres")
    with Session(engine) as db, db.begin():
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            parser.error("La identidad ya existe; no se modificará")
        institution = Institution(name=args.institution)
        user = User(email=email, name=args.name, password_hash=hasher.hash(password))
        db.add_all([institution, user])
        db.flush()
        db.add(Membership(user_id=user.id, institution_id=institution.id, role=args.role))
    print("Institución y administrador creados. Sin credenciales predeterminadas.")


if __name__ == "__main__":
    main()
