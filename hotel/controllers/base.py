"""Session, permission and record helpers shared by all Controllers."""
from contextlib import contextmanager
from hotel.models.database import SessionLocal
from hotel.models.entities import User


class BaseController:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or SessionLocal
        self.user = None  # Snapshot của nhân viên; không giữ Session/ORM trong View.

    @contextmanager
    def _session(self):
        with self.session_factory() as db:
            try:
                yield db
            except Exception:
                db.rollback()
                raise

    def _require_staff(self, db, admin=False):
        if not self.user:
            raise PermissionError('Chỉ nhân viên được thực hiện thao tác này.')
        u = db.get(User, self.user['id'])
        if not u or not u.active or u.role not in ('admin', 'receptionist'):
            self.user = None
            raise PermissionError('Tài khoản không còn quyền truy cập.')
        if admin and u.role != 'admin':
            raise PermissionError('Chức năng chỉ dành cho Admin.')
        return u.id

    @staticmethod
    def _must(db, model, row_id):
        obj = db.get(model, int(row_id))
        if obj is None:
            raise ValueError('Bản ghi không tồn tại.')
        return obj
