"""N5 chatbot entry points for the existing DesktopController.

MySQL persistence + Gemini intent planner. Every DB operation is controlled by
Python and an authenticated user role; booking creates require confirmation.
"""
from __future__ import annotations

import json
import os
from uuid import uuid4
from datetime import timedelta

from sqlalchemy import select
from hotel.models.entities import Booking, Customer, HotelService, BookingPromotion, ServiceOrder
from hotel.services import business, pdf_service
from pathlib import Path

from hotel.models.chat import ChatSession, ChatMessage, ChatToolCall
from hotel.models.common import utc_now
from hotel.services import chatbot as legacy_chatbot
from hotel.services.chatbot_engine import execute, wants_to_book, booking_fields, booking_dialogue, mutation_intent, staff_booking_dialogue
from hotel.services.gemini_client import GeminiError, ROLE_ACTIONS, plan_message, fallback_plan


def _as_json(value):
    try:
        return json.loads(value or '{}')
    except (TypeError, ValueError):
        return {}


class ChatControllerMixin:
    # Backward compatibility for existing tests/external screens that call this.
    # The new GUI uses chat_send() for Gemini + persistent role-scoped sessions.
    def ask_chatbot(self, message):
        with self._session() as db:
            return legacy_chatbot.reply(db, message)

    def _chat_identity(self, db):
        if not self.user:
            return 'guest', None
        user = self._require_user(db)
        if user.must_change_password:
            raise PermissionError('Bạn phải đổi mật khẩu tạm trước khi sử dụng chatbot.')
        role = user.role
        if role not in ROLE_ACTIONS:
            raise PermissionError('Vai trò không được hỗ trợ.')
        return role, user.id

    @staticmethod
    def _chat_session(db, public_id, role, user_id):
        session = db.scalar(select(ChatSession).where(ChatSession.public_id == str(public_id)))
        if not session or session.role_context != role or session.user_id != user_id:
            raise PermissionError('Phiên trò chuyện không thuộc tài khoản hiện tại. Hãy tạo chat mới.')
        return session

    def chat_send(self, message, session_id=None):
        message = str(message).strip()
        if not message or len(message) > 1000:
            raise ValueError('Tin nhắn cần có từ 1 đến 1000 ký tự.')
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            if session_id:
                session = self._chat_session(db, session_id, role, user_id)
            else:
                session = ChatSession(public_id=str(uuid4()), role_context=role, user_id=user_id)
                db.add(session)
                db.flush()
            recent = list(reversed(db.scalars(select(ChatMessage)
                          .where(ChatMessage.session_id == session.id)
                          .order_by(ChatMessage.id.desc()).limit(8)).all()))
            history = [(m.sender, m.content) for m in recent if m.sender == 'user']
            context = _as_json(session.context_json)
            session.updated_at = utc_now()
            public_id = session.public_id
            db.add(ChatMessage(session_id=session.id, sender='user', content=message))
            db.commit()

        # V5: account gate is evaluated BEFORE calling Gemini (including fallback).
        # Pricing / room search remain public. A booking request never calls
        # a date parser or booking tool for unauthenticated guests.
        mutation = mutation_intent(message, role)
        guest_booking_gate = role == 'guest' and wants_to_book(message)
        staff_booking_flow = role in ('admin','receptionist') and (
            wants_to_book(message) or bool(context.get('staff_booking_flow')))
        customer_booking_flow = role == 'customer' and (
            wants_to_book(message) or bool(context.get('booking_flow')))
        if mutation:
            plan = {'action': 'mutation_prepare', 'args': mutation}
        elif guest_booking_gate:
            plan = {'action': 'login_gate', 'args': {}}
        elif staff_booking_flow:
            plan = {'action': 'staff_booking_dialogue', 'args': {}}
        elif customer_booking_flow:
            plan = {'action': 'booking_dialogue', 'args': {}}
        else:
            # Do not hold a DB transaction open while waiting on the network.
            api_enabled = bool(os.environ.get('GEMINI_API_KEY','').strip())
            if api_enabled:
                try:
                    plan = plan_message(role, message, history, context)
                except GeminiError:
                    plan = fallback_plan(role, message, history, context)
            else:
                plan = fallback_plan(role, message, history, context)

        action, args = plan['action'], plan['args']
        with self._session() as db:
            # Revalidate identity after the API response (the user might log out).
            fresh_role, fresh_id = self._chat_identity(db)
            if fresh_role != role or fresh_id != user_id:
                raise PermissionError('Phiên đăng nhập đã thay đổi. Vui lòng mở chat mới.')
            session = self._chat_session(db, public_id, role, user_id)
            context = _as_json(session.context_json)
            pending_request = None
            try:
                if action == 'login_gate':
                    # Preserve only non-personal selections from a guest session.
                    previous = context.get('quote') or context.get('search') or {}
                    selected = booking_fields(message, previous)
                    selected['intent'] = 'booking'
                    self._chat_booking_handoff = selected
                    reply_text = ('Để đặt phòng, bạn cần ĐĂNG NHẬP hoặc ĐĂNG KÝ tài khoản '
                                  'khách hàng trước. Nhấn nút “Đăng nhập / Đăng ký” bên dưới. '
                                  'Sau khi đăng nhập, tôi sẽ tiếp tục hỏi thông tin đặt phòng. '
                                  'Chưa có đơn nào được tạo.')
                    changes = {'booking_flow': None}
                elif action == 'mutation_prepare':
                    reply_text, pending_request = self._chat_prepare_mutation(db, role, user_id, args)
                    changes = {}
                elif action == 'staff_booking_dialogue':
                    reply_text, changes, pending_request = staff_booking_dialogue(
                        db, role, user_id, message, context)
                elif action == 'booking_dialogue':
                    reply_text, changes, pending_request = booking_dialogue(
                        db, role, user_id, message, context)
                elif action == 'reply':
                    reply_text = plan.get('reply','').strip() or 'Bạn cần hỗ trợ nghiệp vụ nào?'
                    changes = {}
                elif role == 'guest' and action == 'booking_prepare':
                    previous = context.get('quote') or context.get('search') or {}
                    selected = booking_fields(message, {**previous, **args})
                    selected['intent'] = 'booking'
                    self._chat_booking_handoff = selected
                    reply_text = ('Vui lòng ĐĂNG NHẬP hoặc ĐĂNG KÝ trước khi đặt phòng. '
                                  'Sau đăng nhập tôi sẽ tiếp tục cuộc hội thoại. Chưa tạo đơn.')
                    changes = {}
                else:
                    reply_text, changes, pending_request = execute(db, role, user_id,
                                                                   action, args, context)
            except (ValueError, PermissionError) as exc:
                reply_text, changes = str(exc), {}
            context.update(changes)
            login_required = bool(role == 'guest' and action in ('login_gate', 'booking_prepare'))
            if login_required and action == 'booking_prepare' and changes.get('quote'):
                # Preserve only the public quote; never transport customer data.
                quote = changes['quote']
                self._chat_booking_handoff = {
                    k: quote[k] for k in ('room_id','room_number','checkin','checkout','guests')
                    if k in quote
                }
            session.context_json = json.dumps(context, ensure_ascii=False)
            confirmation = None
            if pending_request and (role == 'guest' or user_id is None):
                # Defense in depth: a tool may never write while anonymous.
                pending_request = None
                login_required = True
                reply_text = 'Bạn cần đăng nhập/đăng ký trước khi đặt phòng. Chưa tạo đơn.'
            if pending_request:
                # Supersede old unconfirmed requests for the same chat session.
                old_calls = db.scalars(select(ChatToolCall).where(
                    ChatToolCall.session_id == session.id,
                    ChatToolCall.status == 'awaiting_confirmation')).all()
                for old in old_calls:
                    old.status = 'cancelled'
                token = str(uuid4())
                tool_name = pending_request.get('_tool', 'create_booking')
                safe_request = {k:v for k,v in pending_request.items() if k != '_tool'}
                db.add(ChatToolCall(session_id=session.id, tool_name=tool_name,
                    arguments_json=json.dumps(safe_request, ensure_ascii=False),
                    status='awaiting_confirmation', confirmation_required=True,
                    confirmed_by_user=False, idempotency_key=token))
                confirmation = {'token': token, 'label': 'Xác nhận đặt phòng' if tool_name == 'create_booking' else 'Xác nhận thao tác', 'otp_required': False}
            elif action != 'reply':
                # The following is only an audit record, not an authorisation.
                db.add(ChatToolCall(session_id=session.id, tool_name=action,
                    arguments_json=json.dumps(args, ensure_ascii=False),
                    status='completed', idempotency_key=str(uuid4()),
                    confirmation_required=False))
            db.add(ChatMessage(session_id=session.id, sender='assistant', content=reply_text))
            db.commit()
            return {'session_id': public_id, 'reply': reply_text,
                    'confirmation': confirmation, 'login_required': login_required}

    def chat_sessions(self):
        """List only the authenticated account's own prior chat sessions."""
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            if not user_id:
                return []  # An anonymous guest cannot browse others' chats.
            rows = db.scalars(select(ChatSession).where(
                ChatSession.user_id == user_id, ChatSession.role_context == role)
                .order_by(ChatSession.updated_at.desc()).limit(20)).all()
            return [{'session_id': row.public_id,
                     'when': row.updated_at.strftime('%d/%m/%Y %H:%M')}
                    for row in rows]

    def chat_history(self, session_id):
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            session = self._chat_session(db, session_id, role, user_id)
            rows = list(reversed(db.scalars(select(ChatMessage).where(
                ChatMessage.session_id == session.id).order_by(ChatMessage.id.desc()).limit(40)).all()))
            return [{'sender': r.sender, 'content': r.content} for r in rows]

    def chat_request_otp(self, session_id, token):
        # Retired in V4. Anonymous bookings are forbidden; registration/login
        # has its own existing N1 OTP flow. Do not re-enable guest booking OTP.
        raise PermissionError('Vui lòng đăng nhập hoặc đăng ký trước khi đặt phòng qua chat.')

    def chat_resume_booking(self):
        """After N1 login, revalidate saved anonymous room selection on MySQL.

        Creates a NEW customer-scoped session, never promotes a guest session.
        Rechecks availability and does NOT write a Booking until explicit click.
        """
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            if role != 'customer' or not user_id:
                raise PermissionError('Chỉ tài khoản khách hàng đã đăng nhập mới được tiếp tục.')
            handoff = getattr(self, '_chat_booking_handoff', None)
            if not handoff:
                return None
            # Clear before processing; a failed quote must not retain stale data.
            self._chat_booking_handoff = None
            session = ChatSession(public_id=str(uuid4()), role_context=role,
                                  user_id=user_id)
            db.add(session)
            db.flush()
            safe_context = {'booking_flow': booking_fields('', handoff)}
            # If visitor has not supplied dates/room, ask one question at a time.
            # If they chose a room, revalidate it before issuing confirmation.
            try:
                if handoff.get('room_number') and handoff.get('checkin') and handoff.get('checkout') and handoff.get('guests'):
                    reply_text, changes, request = execute(
                        db, role, user_id, 'booking_prepare',
                        {'room_id': handoff['room_number'], 'checkin': handoff['checkin'],
                         'checkout': handoff['checkout'], 'guests': handoff['guests']},
                        safe_context)
                    changes['booking_flow'] = None
                else:
                    reply_text, changes, request = booking_dialogue(
                        db, role, user_id, 'Tôi muốn đặt phòng', safe_context)
            except (ValueError, PermissionError) as exc:
                reply_text, changes, request = (
                    'Thông tin phòng đã chọn cần được kiểm tra lại: ' + str(exc) +
                    '. Vui lòng cho biết ngày nhận phòng để bắt đầu lại.',
                    {'booking_flow': {}}, None)
            safe_context.update(changes)
            session.context_json = json.dumps(safe_context, ensure_ascii=False)
            confirmation = None
            if request:
                token = str(uuid4())
                db.add(ChatToolCall(session_id=session.id, tool_name='create_booking',
                    arguments_json=json.dumps(request, ensure_ascii=False),
                    status='awaiting_confirmation', confirmation_required=True,
                    confirmed_by_user=False, idempotency_key=token))
                confirmation = {'token': token, 'label': 'Xác nhận đặt phòng',
                                'otp_required': False}
            db.add(ChatMessage(session_id=session.id, sender='assistant',
                               content=reply_text))
            db.commit()
            return {'session_id': session.public_id, 'reply': reply_text,
                    'confirmation': confirmation}

    def _chat_prepare_mutation(self, db, role, user_id, args):
        """Validate ownership/state BEFORE showing a one-time confirmation button."""
        tool = args.get('tool')
        if role == 'guest' or not user_id:
            raise PermissionError('Vui lòng đăng nhập để thực hiện yêu cầu.')
        booking = db.scalar(select(Booking).where(Booking.code == str(args.get('code','')).upper()))
        if not booking:
            raise ValueError('Không tìm thấy mã đặt phòng.')
        if role == 'customer' and not db.scalar(select(Customer.id).where(
                Customer.id == booking.customer_id, Customer.user_id == user_id)):
            raise PermissionError('Bạn chỉ được thao tác trên đơn của chính mình.')
        if tool == 'booking_date_help':
            return ('Để đổi lịch, hãy gửi một tin nhắn gồm mã đơn và cả ngày nhận/trả mới. '
                    'Ví dụ: đổi ngày đơn ' + booking.code + ' sang 21/11/2026 đến 23/11/2026.', None)
        if tool == 'booking_change_dates':
            from datetime import date
            if role == 'customer' and not db.scalar(select(Customer.id).where(
                    Customer.id == booking.customer_id, Customer.user_id == user_id)):
                raise PermissionError('Bạn chỉ được đổi ngày đơn của chính mình.')
            if booking.status != 'pending' or booking.invoice is not None:
                raise ValueError('Chỉ được đổi ngày đơn đang chờ, chưa lập hóa đơn.')
            if db.get(BookingPromotion, booking.id) or db.scalar(select(ServiceOrder.id).where(
                    ServiceOrder.booking_id == booking.id, ServiceOrder.status.in_(('pending','confirmed')))):
                raise ValueError('Đơn có khuyến mãi hoặc yêu cầu dịch vụ đang xử lý; vui lòng liên hệ lễ tân để đổi lịch.')
            start, end = date.fromisoformat(args['checkin']), date.fromisoformat(args['checkout'])
            business.dates_in_order(start, end)
            if db.scalar(business.conflicting_query(booking.room_id, start, end).where(
                    Booking.id != booking.id)) is not None:
                raise ValueError('Phòng đã có lịch trùng trong khoảng ngày mới.')
            return (f'Đổi lịch đơn {booking.code} thành {start:%d/%m/%Y}–{end:%d/%m/%Y}? '
                    'Giá phòng/đêm hiện giữ theo đơn gốc; tổng tiền thay đổi theo số đêm.',
                    {'_tool': tool, 'code': booking.code, 'checkin': start.isoformat(), 'checkout': end.isoformat()})
        if tool == 'customer_cancel':
            if role != 'customer' or not db.scalar(select(Customer.id).where(
                    Customer.id == booking.customer_id, Customer.user_id == user_id)):
                raise PermissionError('Bạn chỉ được hủy đơn thuộc tài khoản của mình.')
            if booking.status != 'pending' or booking.invoice is not None:
                raise ValueError('Chatbot chỉ cho phép khách tự hủy đơn đang chờ, chưa lập hóa đơn. Vui lòng liên hệ lễ tân.')
            if db.get(BookingPromotion, booking.id) or db.scalar(select(ServiceOrder.id).where(
                    ServiceOrder.booking_id == booking.id, ServiceOrder.status.in_(('pending','confirmed')))):
                raise ValueError('Đơn có khuyến mãi hoặc dịch vụ đang xử lý; vui lòng liên hệ lễ tân để hủy.')
            return (f'Bạn có chắc muốn HỦY đặt phòng {booking.code}? Thao tác sẽ đổi trạng thái đơn.',
                    {'_tool': tool, 'code': booking.code})
        if role not in ('admin','receptionist'):
            raise PermissionError('Chức năng chỉ dành cho nhân viên.')
        if tool == 'staff_status':
            status = str(args.get('status',''))
            allowed = {'pending': {'confirmed','cancelled'}, 'confirmed': {'checked_in','cancelled'},
                       'checked_in': {'checked_out'}}
            if status not in allowed.get(booking.status, set()):
                raise ValueError(f'Không thể chuyển từ {booking.status} sang {status}.')
            if status == 'checked_out' and (booking.invoice is None or business.invoice_due(booking.invoice) > 0):
                raise ValueError('Không thể trả phòng khi chưa lập và thanh toán đủ hóa đơn.')
            return (f'Nhân viên xác nhận đổi trạng thái đơn {booking.code}: {booking.status} → {status}?',
                    {'_tool': tool, 'code': booking.code, 'status': status})
        if tool == 'staff_add_service':
            service = db.get(HotelService, int(args['service_id']))
            qty = int(args['quantity'])
            if not service or not service.active or not 1 <= qty <= 100:
                raise ValueError('Dịch vụ hoặc số lượng không hợp lệ.')
            if booking.status != 'checked_in' or booking.invoice is not None:
                raise ValueError('Chỉ ghi dịch vụ khi đã nhận phòng và chưa chốt hóa đơn.')
            return (f'Ghi nhận {qty} × {service.name} ({service.price:,.0f}đ/đơn vị) cho {booking.code}?',
                    {'_tool': tool, 'code': booking.code, 'service_id': service.id, 'quantity': qty})
        raise ValueError('Thao tác chưa được hỗ trợ.')

    def _chat_execute_mutation(self, tool, args, role, user_id):
        with self._session() as db:
            new_role, new_id = self._chat_identity(db)
            if (new_role, new_id) != (role, user_id):
                raise PermissionError('Phiên đăng nhập đã thay đổi.')
            booking = db.scalar(select(Booking).where(
                Booking.code == str(args['code']).upper()).with_for_update())
            if not booking:
                raise ValueError('Đơn đặt phòng không tồn tại.')
            if tool == 'booking_change_dates':
                from datetime import date
                from hotel.models.entities import Room
                start, end = date.fromisoformat(args['checkin']), date.fromisoformat(args['checkout'])
                business.dates_in_order(start, end)
                if role == 'customer' and not db.scalar(select(Customer.id).where(
                        Customer.id == booking.customer_id, Customer.user_id == user_id)):
                    raise PermissionError('Không thể đổi ngày cho đơn của tài khoản khác.')
                if role not in ('customer','receptionist','admin') or booking.status != 'pending' or booking.invoice is not None:
                    raise ValueError('Chỉ đổi ngày đơn chờ, chưa lập hóa đơn.')
                if db.get(BookingPromotion, booking.id) or db.scalar(select(ServiceOrder.id).where(
                        ServiceOrder.booking_id == booking.id, ServiceOrder.status.in_(('pending','confirmed')))):
                    raise ValueError('Đơn có khuyến mãi hoặc dịch vụ đang xử lý; không đổi lịch qua chatbot.')
                db.scalar(select(Room).where(Room.id == booking.room_id).with_for_update())
                if db.scalar(business.conflicting_query(booking.room_id, start, end).where(
                        Booking.id != booking.id)) is not None:
                    raise ValueError('Phòng không còn trống trong khoảng ngày mới.')
                booking.checkin_date, booking.checkout_date = start, end
                business.log_event(db, user_id, 'booking.reschedule', booking.code)
                db.commit()
                return f'Đã đổi lịch {booking.code} thành {start:%d/%m/%Y}–{end:%d/%m/%Y}.', None
            if tool == 'customer_cancel':
                if role != 'customer' or not db.scalar(select(Customer.id).where(
                        Customer.id == booking.customer_id, Customer.user_id == user_id)):
                    raise PermissionError('Bạn chỉ được hủy đơn thuộc tài khoản của mình.')
                if booking.status != 'pending' or booking.invoice is not None:
                    raise ValueError('Đơn không còn đủ điều kiện tự hủy.')
                if db.get(BookingPromotion, booking.id) or db.scalar(select(ServiceOrder.id).where(
                        ServiceOrder.booking_id == booking.id, ServiceOrder.status.in_(('pending','confirmed')))):
                    raise ValueError('Đơn có khuyến mãi/dịch vụ, cần lễ tân hỗ trợ hủy.')
                business.change_booking_status(db, booking, 'cancelled', user_id)
                return f'Đã hủy đơn {booking.code}.', None
            if role not in ('admin','receptionist'):
                raise PermissionError('Chỉ nhân viên được thực hiện thao tác này.')
            if tool == 'staff_status':
                business.change_booking_status(db, booking, args['status'], user_id)
                return f'Đã cập nhật {booking.code} → {args["status"]}.', None
            if tool == 'staff_add_service':
                service = db.get(HotelService, int(args['service_id']))
                if service is None:
                    raise ValueError('Không tồn tại dịch vụ.')
                business.add_service_usage(db, booking, service, int(args['quantity']), user_id)
                return f'Đã thêm dịch vụ {service.name} vào {booking.code}.', None
            raise ValueError('Lệnh không hợp lệ.')

    def chat_export_revenue_pdf(self, date_from, date_to, output_path):
        """Admin only; reuse the existing official PDF report generator."""
        from datetime import date
        start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
        if start > end or (end - start).days > 366:
            raise ValueError('Khoảng thống kê phải hợp lệ và tối đa 366 ngày.')
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            if role != 'admin':
                raise PermissionError('Chỉ Admin được xuất báo cáo doanh thu.')
            payments, total = business.revenue_summary(db, start, end)
            content = pdf_service.report_pdf(start, end, payments, total)
        destination = Path(output_path).expanduser().resolve()
        if destination.suffix.lower() != '.pdf':
            raise ValueError('Vui lòng chọn đường dẫn tệp PDF.')
        destination.write_bytes(content)
        return {'reply': f'Đã xuất báo cáo doanh thu: {destination}', 'confirmation': None}

    def chat_confirm(self, session_id, token, otp=None):
        # The token is a one-time authorization, scoped to a live user session.
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            session = self._chat_session(db, session_id, role, user_id)
            call = db.scalar(select(ChatToolCall).where(
                ChatToolCall.session_id == session.id,
                ChatToolCall.idempotency_key == str(token)).with_for_update())
            if not call or call.status != 'awaiting_confirmation':
                raise ValueError('Yêu cầu đã được xử lý hoặc không còn hiệu lực.')
            if utc_now() - call.created_at > timedelta(minutes=15):
                call.status = 'cancelled'
                db.commit()
                raise ValueError('Yêu cầu đã quá 15 phút, hãy thao tác lại.')
            if role == 'guest' or not user_id:
                raise PermissionError('Phải đăng nhập mới được thực hiện yêu cầu.')
            tool = call.tool_name
            values = _as_json(call.arguments_json)
            if tool not in ('create_booking','customer_cancel','staff_status','staff_add_service','booking_change_dates'):
                raise PermissionError('Loại thao tác chưa được hỗ trợ.')
            if tool == 'create_booking' and role not in ('customer','receptionist','admin'):
                raise PermissionError('Vai trò không hợp lệ để đặt phòng.')
            if tool == 'create_booking' and role == 'customer':
                values.pop('customer_id', None)
                values.update({'name':'', 'phone':'', 'email':''})
                values.pop('guest_otp', None)
            # Single-flight: commit processing status before separate booking transaction.
            call.status = 'processing'
            call.confirmed_by_user = True
            db.commit()
        try:
            if tool == 'create_booking':
                # Persist a unique reference in Booking.notes so a crash after
                # business commit can be reconciled without issuing a second booking.
                reference = 'N5REF:' + str(token)
                values['notes'] = (str(values.get('notes',''))[:850] + '\n' + reference).strip()
                with self._session() as db:
                    already = db.scalar(select(Booking.code).where(Booking.notes.like('%' + reference + '%')))
                if already:
                    result = f'Đơn {already} đã được tạo trước đó; không tạo trùng.'
                else:
                    code = self.book(values)
                    result = f'✅ Đã tạo đặt phòng {code} thành công. Hãy kiểm tra trạng thái đơn.'
            else:
                result, _ = self._chat_execute_mutation(tool, values, role, user_id)
            status = 'completed'
        except Exception as exc:
            # Business may have committed before a network/GUI exception.
            # Check the one-time booking reference before reporting failure.
            already = None
            if tool == 'create_booking':
                try:
                    with self._session() as db:
                        already = db.scalar(select(Booking.code).where(
                            Booking.notes.like('%N5REF:' + str(token) + '%')))
                except Exception:
                    pass
            if already:
                result = f'✅ Đặt phòng {already} đã được lưu; không tạo trùng.'
                status = 'completed'
            else:
                result = 'Không thể hoàn tất yêu cầu: ' + str(exc)
                status = 'failed'
        with self._session() as db:
            role2, uid2 = self._chat_identity(db)
            session = self._chat_session(db, session_id, role2, uid2)
            call = db.scalar(select(ChatToolCall).where(
                ChatToolCall.session_id == session.id,
                ChatToolCall.idempotency_key == str(token)))
            if call:
                call.status, call.result_text = status, result
            db.add(ChatMessage(session_id=session.id, sender='assistant', content=result))
            db.commit()
        return {'session_id': session_id, 'reply': result, 'confirmation': None}

    def chat_cancel(self, session_id, token):
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            session = self._chat_session(db, session_id, role, user_id)
            call = db.scalar(select(ChatToolCall).where(
                ChatToolCall.session_id == session.id,
                ChatToolCall.idempotency_key == str(token)).with_for_update())
            if not call or call.status != 'awaiting_confirmation':
                raise ValueError('Yêu cầu đã hết hiệu lực.')
            call.status = 'cancelled'
            reply_text = 'Đã hủy yêu cầu xác nhận. Chưa thực hiện thao tác ghi dữ liệu từ yêu cầu này.'
            db.add(ChatMessage(session_id=session.id, sender='assistant', content=reply_text))
            db.commit()
            return {'session_id': session_id, 'reply': reply_text, 'confirmation': None}
