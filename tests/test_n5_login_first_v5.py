"""Standalone safety regression tests: no database/network required."""
import ast
import re
import unittest
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
HOTEL = ROOT/'overlay/hotel' if (ROOT/'overlay/hotel').exists() else ROOT/'hotel'
SOURCE = HOTEL/'services/chatbot_engine.py'
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
subset = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in
          ('_booking_plain', 'wants_to_book', 'booking_fields', 'booking_dialogue')]
namespace = {'re': re, 'date': date, 'timedelta': timedelta, 'unicodedata': unicodedata,
             'business': SimpleNamespace(dates_in_order=lambda a, b: None)}
exec(compile(ast.Module(body=subset, type_ignores=[]), str(SOURCE), 'exec'), namespace)

class LoginFirstV5Tests(unittest.TestCase):
    def test_01_unauthenticated_booking_detected(self):
        self.assertTrue(namespace['wants_to_book']('tôi muốn đặt phòng'))
        self.assertTrue(namespace['wants_to_book']('OK cho tôi phòng 102'))
        self.assertTrue(namespace['wants_to_book']('Tôi muốn đặt phòng cho 3 người từ ngày mai ở 3 đêm'))

    def test_02_public_browsing_remains_public(self):
        for q in ('Giá phòng Deluxe bao nhiêu?', 'tìm phòng trống ngày mai', 'xem phòng VIP'):
            self.assertFalse(namespace['wants_to_book'](q))

    def test_03_customer_booking_starts_with_question_not_date_error(self):
        result = namespace['booking_dialogue'](None, 'customer', 42, 'tôi muốn đặt phòng', {})
        self.assertIn('ngày nào', result[0])
        self.assertIsNone(result[2])

    def test_04_unauthenticated_dialogue_never_executes(self):
        namespace['execute'] = Mock(side_effect=AssertionError('must not execute'))
        self.assertIsNone(namespace['booking_dialogue'](None, 'guest', None, 'tôi muốn đặt phòng', {}))
        namespace['execute'].assert_not_called()

    def test_05_resume_after_login_with_no_selected_room(self):
        result = namespace['booking_dialogue'](None, 'customer', 42, 'Tôi muốn đặt phòng',
                                               {'booking_flow': {'intent':'booking'}})
        self.assertIn('ngày nào', result[0])

    def test_06_multiple_turns_slot_filling(self):
        p = namespace['booking_dialogue'](None, 'customer', 42, 'Tôi muốn đặt phòng', {})
        p2 = namespace['booking_dialogue'](None, 'customer', 42, 'ngày mai 3 đêm', p[1])
        self.assertIn('bao nhiêu khách', p2[0])
        self.assertEqual((date.fromisoformat(p2[1]['booking_flow']['checkout']) -
                          date.fromisoformat(p2[1]['booking_flow']['checkin'])).days, 3)
        def fake_execute(db, role, uid, action, args, context):
            self.assertEqual(action, 'room_search')
            return 'Phòng 102 còn trống', {'search': args}, None
        namespace['execute'] = fake_execute
        p3 = namespace['booking_dialogue'](None, 'customer', 42, '2 người', p2[1])
        self.assertIn('Phòng 102 còn trống', p3[0])
        self.assertIsNone(p3[2])

    def test_07_room_confirmation_never_self_executes_booking(self):
        slots = {'checkin': (date.today()+timedelta(days=1)).isoformat(),
                 'checkout': (date.today()+timedelta(days=2)).isoformat(), 'guests':2}
        prepared = {'room_id': 7, 'checkin': slots['checkin'], 'checkout': slots['checkout'], 'guests':2}
        def fake_execute(db, role, uid, action, args, context):
            self.assertEqual(action, 'booking_prepare')
            return 'Bấm xác nhận đặt phòng', {'quote': args}, prepared
        namespace['execute'] = fake_execute
        result = namespace['booking_dialogue'](None, 'customer', 42, 'cho tôi phòng 102', {'booking_flow':slots})
        self.assertEqual(result[2], prepared)
        self.assertIn('xác nhận', result[0])

    def test_08_controller_pre_gemini_gate_present(self):
        controller = (SOURCE.parents[1]/'controllers/chat_controller.py').read_text(encoding='utf-8')
        self.assertLess(controller.index('guest_booking_gate ='), controller.index('plan_message(role, message'))
        self.assertIn("plan = {'action': 'login_gate'", controller)
        self.assertIn("if role == 'guest' or not user_id:", controller)

if __name__ == '__main__':
    unittest.main()
