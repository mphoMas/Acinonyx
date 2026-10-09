"""Selected static-preview browser regressions; not production qualification."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2] / 'public' / 'design-preview'
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
checks = 0
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page()
        failures = []
        page.on('pageerror', lambda error: failures.append(str(error)))
        for width in (320, 360, 768, 1440):
            page.set_viewport_size({'width':width,'height':900})
            page.goto(f'http://127.0.0.1:{server.server_port}')
            for view in ('today','reservations','billing','housekeeping','portfolio'):
                page.locator(f'[data-view="{view}"]').click()
                assert page.locator('h1').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), (width,view)
                checks += 1
        for state in ('loading','empty','error','denied','stale','conflict','pending','unknown'):
            page.locator('#scenario').select_option(state)
            assert page.locator('[role="status"]').count() >= 1
            if state in ('loading','empty','error','denied'):
                assert page.locator('table').count() == 0
            checks += 1
        page.locator('#scenario').select_option('ready')
        page.locator('[data-view="reservations"]').click()
        page.locator('#new-reservation').click()
        page.locator('#guest').fill('Fictional test')
        page.locator('#arrival').fill('2026-10-09')
        page.locator('#departure').fill('2026-10-10')
        # Native modal must keep keyboard focus inside, including backwards navigation.
        page.keyboard.press('Shift+Tab')
        assert page.evaluate("document.activeElement.closest('#reservation-dialog') !== null")
        checks += 1
        page.locator('[type="submit"]').click()
        first = page.locator('#form-feedback').inner_text()
        page.locator('[type="submit"]').click()
        assert page.locator('#form-feedback').inner_text() == first
        checks += 1
        page.locator('#close-reservation').click()
        page.locator('#property').select_option('sample-b')
        assert page.locator('#switch-dialog').evaluate('(d)=>d.open')
        page.keyboard.press('Escape')
        assert page.locator('#property').input_value() == 'sample-a'
        checks += 1
        page.locator('#property').select_option('sample-b')
        page.locator('#discard-draft').click()
        assert page.locator('#guest').input_value() == ''
        assert 'A101' not in page.locator('main').inner_text()
        assert 'B201' in page.locator('main').inner_text()
        checks += 1
        page.locator('#role').select_option('housekeeping')
        assert page.locator('[data-view]').count() == 1
        assert 'Sample Guest' not in page.locator('main').inner_text()
        checks += 1
        page.emulate_media(reduced_motion='reduce')
        page.set_viewport_size({'width':360,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        checks += 1
        page.set_viewport_size({'width':1440,'height':900})
        page.evaluate("document.body.style.zoom='2'")
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        checks += 1
        page.evaluate("document.body.style.zoom='1'")
        # Keyboard entry starts at the skip link and moves to the main workspace.
        page.reload()
        page.keyboard.press('Tab')
        assert page.locator('.skip').evaluate('(a)=>a===document.activeElement')
        page.keyboard.press('Enter')
        assert page.locator('#workspace').evaluate('(m)=>m===document.activeElement')
        checks += 1
        output = os.environ.get('PLG_SCREENSHOT_DIR')
        if output:
            target = Path(output)
            target.mkdir(parents=True, exist_ok=True)
            for width in (360,1440):
                page.set_viewport_size({'width':width,'height':900})
                page.locator('#role').select_option('manager')
                page.locator('[data-view="today"]').click()
                page.evaluate('document.activeElement.blur()')
                page.screenshot(path=str(target / f'today-{width}.png'), full_page=True)
        assert not failures, failures
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print(f'{checks} browser checks passed; no JavaScript page errors')
