# backend/app/cli.py
import argparse
import sys

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.stammdaten import User


def create_admin(name: str, email: str, password: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            User.deleted_at.is_(None),
            (User.email == email) | (User.name == name),
        ).first()
        if existing:
            print(f"User mit E-Mail {email} oder Name {name} existiert bereits.")
            sys.exit(1)

        admin = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            must_change_password=False,
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        print(f"Admin '{name}' ({email}) angelegt.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Immobilien-Verwaltung CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-admin")
    p.add_argument("--name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)

    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.name, args.email, args.password)


if __name__ == "__main__":
    main()