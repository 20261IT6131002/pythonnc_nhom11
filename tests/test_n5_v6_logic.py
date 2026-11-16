"""Standalone V6 checks (no network, no live MySQL)."""
import ast
import re
import unicodedata
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
HOTEL = ROOT/'overlay/hotel' if (ROOT/'overlay/hotel').exists() else ROOT/'hotel'
SOURCE = HOTEL/'services/chatbot_engine.py'
CONTROLLER = HOTEL/'controllers/chat_controller.py'
source = SOURCE.read_text(encoding='utf-8')
functions = {'_booking_plain', 'wants_to_book', 'booking_fields', 'booking_dialogue',
             'mutation_intent', 'staff_booking_dialogue'}
tree = ast.parse(source)
funcs = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in functions]

def dates_in_order(a,b):
    if a < date.today() or b <= a:
        raise ValueError('Ngày trả phòng phải sau ngày nhận phòng hoặc ngày nhận quá khứ.')

ns = {'re':re, 'unicodedata':unicodedata, 'date':date, 'timedelta':timedelta,
      'business':SimpleNamespace(dates_in_order=dates_in_order)}
exec(compile(ast.Module(body=funcs, type_ignores=[]), str(SOURCE), 'exec'), ns)

class V6Regressions(unittest.TestCase):
    def test_guest_wants_booking(self):
        for msg in ['Tôi muốn đặt phòng', 'cho tôi phòng 102', 'chốt phòng 301']:
            self.assertTrue(ns['wants_to_book'](msg), msg)

    def test_browsing_only_not_forced_to_login(self):
        for msg in ['Tìm phòng trống', 'Giá phòng VIP', 'Xem phòng 102']:
            self.assertFalse(ns['wants_to_book'](msg), msg)

    def test_followup_date_is_checkout(self):
        d = (date.today()+timedelta(days=3)).isoformat()
        end = (date.today()+timedelta(days=5)).isoformat()
        slots = ns['booking_fields'](end, {'checkin':d})
        self.assertEqual(slots['checkin'],d)
        self.assertEqual(slots['checkout'],end)

    def test_two_dates_are_ordered(self):
        d = date.today()+timedelta(days=5)
        slots=ns['booking_fields'](f'{d:%d/%m/%Y} đến {d+timedelta(days=3):%d/%m/%Y}')
        self.assertEqual(slots['checkin'],d.isoformat())
        self.assertEqual(slots['checkout'],(d+timedelta(days=3)).isoformat())

    def test_relative_date_and_nights(self):
        slots=ns['booking_fields']('ngày mai ở 3 đêm, 2 khách')
        self.assertEqual(slots['checkin'],(date.today()+timedelta(days=1)).isoformat())
        self.assertEqual(slots['checkout'],(date.today()+timedelta(days=4)).isoformat())
        self.assertEqual(slots['guests'],2)

    def test_customer_multiturn_checkout(self):
        start=(date.today()+timedelta(days=5)).isoformat()
        end=(date.today()+timedelta(days=7)).isoformat()
        p1=ns['booking_dialogue'](None,'customer',42,'Tôi muốn đặt phòng',{})
        p2=ns['booking_dialogue'](None,'customer',42,start,p1[1])
        self.assertIn('trả phòng',p2[0])
        p3=ns['booking_dialogue'](None,'customer',42,end,p2[1])
        self.assertIn('bao nhiêu khách',p3[0])
        self.assertEqual(p3[1]['booking_flow']['checkin'],start)
        self.assertEqual(p3[1]['booking_flow']['checkout'],end)

    def test_invalid_dates_ask_again(self):
        start=(date.today()+timedelta(days=4)).isoformat()
        older=(date.today()+timedelta(days=1)).isoformat()
        p=ns['booking_dialogue'](None,'customer',42,older,{'booking_flow':{'checkin':start,'active':True}})
        self.assertIn('Ngày',p[0]);self.assertIsNone(p[1]['booking_flow']['checkout'])

    def test_staff_collects_missing_fields(self):
        p=ns['staff_booking_dialogue'](None,'receptionist',1,'tôi muốn đặt phòng',{})
        self.assertIn('ngày nào',p[0]);self.assertIsNone(p[2])
        ns['execute']=lambda db,role,uid,action,args,context: ('Danh sách phòng trống',{},None)
        q=ns['staff_booking_dialogue'](None,'receptionist',1,'ngày mai ở 2 đêm 2 người',p[1])
        self.assertIn('phòng số',q[0]); self.assertIsNone(q[2])

    def test_staff_and_guest_not_confused(self):
        self.assertIsNone(ns['staff_booking_dialogue'](None,'guest',None,'đặt phòng',{}))
        self.assertIsNone(ns['booking_dialogue'](None,'guest',None,'đặt phòng',{}))

    def test_customer_cancel_intent(self):
        item=ns['mutation_intent']('Hủy đơn BK-123456789A','customer')
        self.assertEqual(item,{'tool':'customer_cancel','code':'BK-123456789A'})

    def test_staff_workflows(self):
        for q,status in [('Xác nhận đơn','confirmed'),('Check-in','checked_in'),
                         ('Check-out','checked_out'),('Hủy đơn','cancelled')]:
            item=ns['mutation_intent'](q+' BK-123456789A','receptionist')
            self.assertEqual(item['status'],status,q)

    def test_guest_never_mutates(self):
        self.assertIsNone(ns['mutation_intent']('Hủy đơn BK-123456789A','guest'))

    def test_service_quantity(self):
        item=ns['mutation_intent']('Thêm dịch vụ 5 x 2 cho BK-123456789A','admin')
        self.assertEqual(item['tool'],'staff_add_service')
        self.assertEqual(item['service_id'],5)
        self.assertEqual(item['quantity'],2)

    def test_reschedule_both_dates(self):
        item=ns['mutation_intent']('Đổi ngày đơn BK-123456789A sang 21/12/2026 đến 23/12/2026','customer')
        self.assertEqual(item['tool'],'booking_change_dates')
        self.assertEqual(item['checkin'],'2026-12-21')
        self.assertEqual(item['checkout'],'2026-12-23')

    def test_reschedule_missing_date_prompts_not_mutation(self):
        item=ns['mutation_intent']('Đổi ngày BK-123456789A sang 21/12/2026','customer')
        self.assertEqual(item['tool'],'booking_date_help')

    def test_mutations_require_confirmation_in_controller(self):
        code=CONTROLLER.read_text(encoding='utf-8')
        self.assertIn("plan = {'action': 'mutation_prepare'",code)
        self.assertIn("status='awaiting_confirmation'",code)
        self.assertIn("tool not in ('create_booking'",code)
        self.assertIn("Booking.notes.like('%N5REF:'",code)
        self.assertIn("def chat_export_revenue_pdf",code)

    def test_role_scoped_pdf(self):
        code=CONTROLLER.read_text(encoding='utf-8')
        self.assertIn("if role != 'admin':",code)
        self.assertIn('pdf_service.report_pdf',code)

if __name__=='__main__':
    unittest.main()
