"""Headless render smoke tests for admin panes; no GUI or real MySQL needed."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from hotel.views.screens import admin as admin_ui


class _FakeAdmin(admin_ui.AdminScreenMixin):
    def __init__(self):
        self.body = object()
        self.account_kind = 'staff'
        self.c = SimpleNamespace(
            user={'id': 99},
            table=lambda _kind: [
                {'id': 1, 'username': 'admin', 'role': 'admin', 'name': 'Quản trị',
                 'email': 'admin@example.com', 'phone': '0900000000',
                 'account_status': 'Hoạt động', 'active': True, 'position': 'Quản lý'},
                {'id': 2, 'username': 'guest', 'role': 'customer', 'name': 'Khách',
                 'email': 'guest@example.com', 'phone': '0911111111',
                 'account_status': 'Hoạt động', 'active': True, 'position': ''},
            ],
            link_requests=lambda: [{'id': 1, 'username': 'guest', 'code': 'BK-1'}],
        )

    def _button(self, *_args, **_kwargs):
        return None


def test_admin_account_tabs_and_link_queue_render_without_missing_globals(monkeypatch):
    buttons = []

    def mock_button(*_args, **kwargs):
        buttons.append(kwargs)
        return MagicMock()

    for kind in ('Frame', 'Canvas', 'Label'):
        monkeypatch.setattr(admin_ui.tk, kind, lambda *_a, **_kw: MagicMock())
    monkeypatch.setattr(admin_ui.tk, 'Button', mock_button)
    for kind in ('Frame', 'Label', 'Scrollbar'):
        monkeypatch.setattr(admin_ui.ttk, kind, lambda *_a, **_kw: MagicMock())
    monkeypatch.setattr(admin_ui, 'add_tree', lambda *_args, **_kw: 'mock_tree')

    view = _FakeAdmin()
    view._accounts_tab()
    assert [row['username'] for row in view.rows] == ['admin']
    assert [button['text'] for button in buttons] == [
        'Nhân viên', 'Khách hàng', '+  Thêm tài khoản nhân viên',
        'Khóa', 'Xóa vĩnh viễn'
    ]

    buttons.clear()
    view.account_kind = 'customer'
    view._accounts_tab()
    assert [row['username'] for row in view.rows] == ['guest']
    assert [button['text'] for button in buttons] == ['Nhân viên', 'Khách hàng']

    view._links_tab()
    assert view.rows[0]['code'] == 'BK-1'
    assert view.tree == 'mock_tree'


def test_account_row_actions_target_only_the_requested_employee(monkeypatch):
    view = _FakeAdmin()
    view.rows = [row for row in view.c.table('users') if row['role'] == 'admin']
    calls = []
    view.c.toggle_user = lambda uid: calls.append(('toggle', uid))
    view.c.delete_staff_permanently = lambda uid: calls.append(('delete', uid))
    view._done = lambda message: calls.append(('done', message))
    view.winfo_toplevel = lambda: None
    monkeypatch.setattr(admin_ui.messagebox, 'askyesno', lambda *_a, **_kw: True)
    monkeypatch.setattr(admin_ui.simpledialog, 'askstring', lambda *_a, **_kw: 'admin')

    view._account_toggle_row(1)
    view._account_delete_row(1)

    assert ('toggle', 1) in calls
    assert ('delete', 1) in calls


def test_permanent_delete_requires_exact_username(monkeypatch):
    import pytest

    view = _FakeAdmin()
    view.rows = [row for row in view.c.table('users') if row['role'] == 'admin']
    view.winfo_toplevel = lambda: None
    called = []
    view.c.delete_staff_permanently = lambda uid: called.append(uid)
    monkeypatch.setattr(admin_ui.simpledialog, 'askstring', lambda *_a, **_kw: 'wrong')
    with pytest.raises(ValueError, match='khớp'):
        view._account_delete_row(1)
    assert called == []


def test_previously_archived_staff_can_still_be_permanently_deleted(monkeypatch):
    buttons = []
    for kind in ('Frame', 'Canvas', 'Label'):
        monkeypatch.setattr(admin_ui.tk, kind, lambda *_a, **_kw: MagicMock())
    monkeypatch.setattr(admin_ui.tk, 'Button', lambda *_a, **kw: (
        buttons.append(kw), MagicMock())[1])
    monkeypatch.setattr(admin_ui.ttk, 'Scrollbar', lambda *_a, **_kw: MagicMock())

    view = _FakeAdmin()
    row = dict(view.c.table('users')[0], account_status='Ngừng sử dụng', active=False)
    view.c.table = lambda _kind: [row]
    view._accounts_tab()

    unlock = next(button for button in buttons if button['text'] == 'Mở')
    delete = next(button for button in buttons if button['text'] == 'Xóa vĩnh viễn')
    assert unlock['state'] == 'disabled'
    assert delete['state'] == 'normal'
