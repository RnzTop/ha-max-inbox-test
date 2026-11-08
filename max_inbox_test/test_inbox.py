import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from inbox import Inbox, Incoming, claimed_payload, message_payload


class InboxTest(unittest.TestCase):
    def test_restart_equal_text_photo_and_atomic_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue.db"
            queue = Inbox(path)
            old = Incoming("test", "dialog", "old", "Тест", "старая переписка")
            queue.receive(old, baseline=True)
            first = Incoming("test", "dialog", "1", "Тест", "MAX HA TEST 8432")
            photo = Incoming("test", "dialog", "2", "Тест", attachment="фото")
            repeated = Incoming("test", "dialog", "3", "Тест", first.text)
            for event in (first, photo, repeated):
                self.assertIsNotNone(queue.receive(event))
            queue = Inbox(path)
            for event in (old, first, photo, repeated):
                self.assertIsNone(queue.receive(event))
            item = queue.reserve_delivery()
            self.assertIn("Взять в работу", str(message_payload(item)))
            self.assertTrue(queue.delivered(item["id"], "group-msg"))
            self.assertFalse(queue.claim(item["id"], "other-msg", "1", "Олег"))
            with ThreadPoolExecutor(max_workers=2) as workers:
                winners = list(workers.map(
                    lambda person: Inbox(path).claim(item["id"], "group-msg", *person),
                    [("1", "Олег"), ("2", "Ирина")],
                ))
            self.assertEqual(sum(winners), 1)
            queue = Inbox(path)
            edit = queue.pending_edit()
            self.assertIn("Взял в работу: ", claimed_payload(edit)["text"])
            self.assertEqual(claimed_payload(edit)["attachments"], [])
            queue.edited(edit["id"], edit["revision"])
            self.assertIsNone(queue.pending_edit())
            photo_item = queue.reserve_delivery()
            self.assertIn("Вложение: фото", photo_item["body"])
            self.assertNotIn("Телефон:", photo_item["body"])
            # The photo delivery is uncertain. Restart does not resend it.
            next_item = Inbox(path).reserve_delivery()
            self.assertIn(first.text, next_item["body"])
            self.assertNotEqual(item["id"], next_item["id"])
            self.assertIsNone(Inbox(path).reserve_delivery())


if __name__ == "__main__":
    unittest.main()
