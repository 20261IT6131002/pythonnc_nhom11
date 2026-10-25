"""Session, permission and record helpers shared by all Controllers."""
from contextlib import contextmanager
from hotel.models.database import SessionLocal
from hotel.models.entities import User
from hotel.services.auth import credential_tag
import hmac


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
        u = self._require_user(db)
        if u.must_change_password:
            raise PermissionError('Bạn phải đổi mật khẩu tạm trước khi dùng nghiệp vụ.')
        if u.role not in ('admin', 'receptionist'):
            raise PermissionError('Chỉ nhân viên được thực hiện thao tác này.')
        if admin and u.role != 'admin':
            raise PermissionError('Chức năng chỉ dành cho Admin.')
        return u.id

    def _require_user(self, db):
        if not self.user:
            raise PermissionError('Vui lòng đăng nhập để tiếp tục.')
        u = db.get(User, self.user['id'])
        if (not u or not u.active or u.archived_at is not None or
                u.role != self.user['role'] or
                not hmac.compare_digest(self.user.get('_credential_tag', ''),
                                        credential_tag(u.password_hash))):
            self.user = None
            raise PermissionError('Tài khoản không còn quyền truy cập.')
        return u

    @staticmethod
    def _must(db, model, row_id):
        obj = db.get(model, int(row_id))
        if obj is None:
            raise ValueError('Bản ghi không tồn tại.')
        return obj
