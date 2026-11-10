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

from hotel.models.chat import ChatSession, ChatMessage, ChatToolCall
from hotel.models.common import utc_now
from hotel.services import chatbot as legacy_chatbot
from hotel.services.chatbot_engine import execute, wants_to_book, booking_fields, booking_dialogue
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
        guest_booking_gate = role == 'guest' and wants_to_book(message)
        customer_booking_flow = role == 'customer' and (
            wants_to_book(message) or bool(context.get('booking_flow')))
        if guest_booking_gate:
            plan = {'action': 'login_gate', 'args': {}}
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
                db.add(ChatToolCall(session_id=session.id, tool_name='create_booking',
                    arguments_json=json.dumps(pending_request, ensure_ascii=False),
                    status='awaiting_confirmation', confirmation_required=True,
                    confirmed_by_user=False, idempotency_key=token))
                confirmation = {'token': token, 'label': 'Xác nhận đặt phòng', 'otp_required': False}
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

    def chat_confirm(self, session_id, token, otp=None):
        # Atomically consume the one-time authorisation before calling the existing
        # N2 booking workflow; a repeated click cannot create a second booking.
        with self._session() as db:
            role, user_id = self._chat_identity(db)
            session = self._chat_session(db, session_id, role, user_id)
            call = db.scalar(select(ChatToolCall).where(
                ChatToolCall.session_id == session.id,
                ChatToolCall.idempotency_key == str(token),
                ChatToolCall.tool_name == 'create_booking').with_for_update())
            if not call or call.status != 'awaiting_confirmation':
                raise ValueError('Yêu cầu này đã được xử lý hoặc không còn hiệu lực.')
            if utc_now() - call.created_at > timedelta(minutes=15):
                call.status = 'cancelled'
                db.commit()
                raise ValueError('Yêu cầu quá 15 phút. Vui lòng tìm phòng và đặt lại.')
            values = _as_json(call.arguments_json)
            if role == 'guest' or user_id is None:
                raise PermissionError('Bạn phải đăng nhập mới được tạo đặt phòng qua chat.')
            if role == 'customer':
                # Never accept contact details from a guest draft or model.
                values.pop('customer_id', None)
                values['name'] = ''
                values['phone'] = ''
                values['email'] = ''
                values.pop('guest_otp', None)
            call.status = 'processing'
            call.confirmed_by_user = True
            db.commit()
        # Important: the booking implementation owns room locks and commits.
        try:
            code = self.book(values)
            result = f'✅ Đã tạo đặt phòng {code} thành công. Vui lòng xem trạng thái đặt phòng để biết bước tiếp theo.'
            status = 'completed'
        except (ValueError, PermissionError) as exc:
            result = f'Không thể tạo đặt phòng: {exc}. Hãy kiểm tra lại thông tin và lập yêu cầu mới.'
            status = 'failed'
        with self._session() as db:
            role2, uid2 = self._chat_identity(db)
            session = self._chat_session(db, session_id, role2, uid2)
            call = db.scalar(select(ChatToolCall).where(ChatToolCall.session_id == session.id,
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
            reply_text = 'Đã hủy yêu cầu tạo đặt phòng. Chưa có đơn nào được ghi từ yêu cầu này.'
            db.add(ChatMessage(session_id=session.id, sender='assistant', content=reply_text))
            db.commit()
            return {'session_id': session_id, 'reply': reply_text, 'confirmation': None}
