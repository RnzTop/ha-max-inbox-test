"""HA ingress test fixture. Only synthetic events can enter this process."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from pathlib import Path
import sys
from urllib.parse import parse_qs

from inbox import Inbox, Incoming


def handler(queue):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, text):
            body = text.encode()
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            with queue.connect() as db:
                rows = db.execute("""
                    SELECT id, body, group_message, employee_name FROM notices
                    WHERE delivery='sent' ORDER BY id
                """).fetchall()
            cards = []
            for row in rows:
                content = '<pre>' + escape(row['body']) + '</pre>'
                if row['employee_name']:
                    content += '<p>Взял в работу: ' + escape(row['employee_name']) + '</p>'
                else:
                    content += f'''<form method="post">
                      <input type="hidden" name="notice" value="{row['id']}">
                      <button name="employee" value="1">Взять в работу — Олег</button>
                      <button name="employee" value="2">Взять в работу — Ирина</button>
                    </form>'''
                cards.append('<article>' + content + '</article>')
            self.respond(200, '''<!doctype html><html lang="ru"><meta charset="utf-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
            <title>MAX — тест уведомлений</title>
            <h1>Стенд уведомлений MAX</h1>
            <p>Искусственные данные. Карточки отображаются в этой панели.</p>
            <form method="post"><button name="sample" value="yes">Загрузить три тестовых сообщения</button></form>
            ''' + ''.join(cards) + '</html>')

        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024:
                    raise ValueError
                values = parse_qs(self.rfile.read(size).decode(), max_num_fields=4)
                if values == {'sample': ['yes']}:
                    for key, text, attachment in (
                        ('1', 'MAX HA TEST 8432', ''),
                        ('2', '', 'фото'),
                        ('3', 'MAX HA TEST 8432', ''),
                    ):
                        queue.receive(Incoming('demo', 'demo', key, 'Тестовый клиент', text, attachment))
                    while (item := queue.reserve_delivery()) is not None:
                        queue.delivered(item['id'], f"demo-{item['id']}")
                else:
                    notice_id = int(values['notice'][0])
                    employee = values['employee'][0]
                    name = {'1': 'Олег', '2': 'Ирина'}[employee]
                    queue.claim(notice_id, f'demo-{notice_id}', employee, name)
            except (KeyError, ValueError):
                self.respond(400, 'Некорректная команда стенда.')
                return
            self.do_GET()

    return Handler


if __name__ == '__main__':
    database, host, port = sys.argv[1:]
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer((host, int(port)), handler(Inbox(database))).serve_forever()
