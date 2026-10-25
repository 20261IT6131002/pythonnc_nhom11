"""Khởi động ứng dụng Tkinter GrandStay."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox


def main() -> None:
    try:
        from hotel.models.database import Base, engine, SessionLocal
        from hotel.models import entities  # noqa: F401
        from hotel.services.n1_core import bootstrap_n1
        from hotel.services.email_schema import migrate_email_columns
        from hotel.controllers.desktop_controller import DesktopController
        from hotel.views.desktop import GrandStayApp

        with engine.connect() as conn:
            conn.exec_driver_sql('SELECT 1')
        migrate_email_columns(engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            bootstrap_n1(db)
    except Exception as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Không kết nối được MySQL',
            'Kiểm tra .env, dịch vụ MySQL và quyền tài khoản.\n\n' + str(exc), parent=root)
        root.destroy()
        raise SystemExit(1) from exc

    app = GrandStayApp(DesktopController())
    app.mainloop()


if __name__ == '__main__':
    main()
