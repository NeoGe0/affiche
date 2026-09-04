import argparse
import logging
import sys

from affiche.app.auth.service.auth_service import AuthError, AuthService
from affiche.app.auth.service.user_repository import UserRepository
from affiche.config.database import SessionLocal, init_db
from affiche.config.logging_config import setup_logging

logger = logging.getLogger("affiche.cli")

def reset_password(username: str | None) -> int:
    session = SessionLocal()
    try:
        service = AuthService(UserRepository(session))
        try:
            name, password = service.reset_password(username)
        except AuthError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    finally:
        session.close()

    logger.warning("Temporary password for %r: %s - sign in with it and choose a new one now",
                   name, password)
    print(f"\n  Username:           {name}")
    print(f"  Temporary password: {password}\n")
    print("Sign in with it; the app will require a new password before anything else.")
    print("Every existing session has been signed out.")
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m affiche.cli", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    reset = subcommands.add_parser(
        "reset-password",
        help="Set a temporary password on an account and print it (forgotten-password recovery)")
    reset.add_argument(
        "--username",
        help="Which account. Optional: with a single admin, the only one is used.")

    args = parser.parse_args(argv)

    init_db()
    setup_logging()

    if args.command == "reset-password":
        return reset_password(args.username)
    parser.error(f"unknown command {args.command!r}")

if __name__ == "__main__":
    sys.exit(main())
