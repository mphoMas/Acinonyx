"""Frontend contract tests with controlled HTTP responses, not live IAM proof."""
from pathlib import Path
import shutil

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def board():
    with sync_playwright() as driver:
        executable = shutil.which('chromium') or shutil.which('google-chrome')
        browser = driver.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        state = {'session': 200, 'mutation': 200, 'posts': [], 'errors': []}
        page.on('pageerror', lambda error: state['errors'].append(str(error)))
        issue = {'key': 'SBA-5', 'title': 'Authenticated board actions', 'description': '',
                 'issue_type': 'TASK', 'priority': 'HIGH', 'current_state': 'BACKLOG'}

        def handle(route):
            request = route.request
            if request.url.endswith('/portal/scrum.html?project=SBA'):
                route.fulfill(body=(ROOT / 'portal/scrum.html').read_text(), content_type='text/html')
            elif request.url.endswith('/api/pm/v1/session'):
                route.fulfill(status=state['session'], json={'principal': 'tenant:operator', 'csrf_token': 'test-csrf'} if state['session'] == 200 else {'error': {'message': 'Session unavailable'}})
            elif request.method == 'POST':
                state['posts'].append({'body': request.post_data_json, 'csrf': request.headers.get('x-csrf-token')})
                route.fulfill(status=state['mutation'], json={'success': True} if state['mutation'] == 200 else {'error': {'message': 'Not authorized'}})
            elif request.url.endswith('/api/pm/projects'):
                route.fulfill(json={'projects': [{'key': 'SBA', 'name': 'Scrum Board Automation'}]})
            elif '/api/pm/board/' in request.url:
                route.fulfill(json={'issues_by_column': {'BACKLOG': [issue]}, 'sprints': []})
            else:
                route.fulfill(status=404, json={'error': 'Not found'})

        page.route('**/*', handle)
        page.goto('http://board.test/portal/scrum.html?project=SBA')
        page.locator('[data-ticket="SBA-5"]').wait_for()
        page.on('dialog', lambda dialog: dialog.accept())
        yield page, state
        browser.close()


def request_transition(page):
    page.locator('[data-ticket="SBA-5"]').click()
    page.locator('#next-state').select_option('REFINED')
    page.locator('#transition').click()


def test_loads_real_board_view_without_script_errors(board):
    page, state = board
    assert page.locator('#project-name').inner_text() == 'Scrum Board Automation'
    assert page.locator('#content').get_attribute('aria-busy') == 'false'
    assert state['errors'] == []


def test_transition_sends_csrf_and_no_claimed_actor(board):
    page, state = board
    request_transition(page)
    page.wait_for_function("document.querySelector('#toast').textContent==='Transition accepted by MAS-PM'")
    assert state['posts'][0]['csrf'] == 'test-csrf'
    assert 'caller_principal' not in state['posts'][0]['body']
    assert not page.locator('#drawer').is_visible()
    assert state['errors'] == []


def test_denied_transition_is_visible_inside_modal(board):
    page, state = board
    state['mutation'] = 403
    request_transition(page)
    page.locator('#drawer-error').wait_for(state='visible')
    assert page.locator('#drawer-error').inner_text() == 'Rejected: Not authorized'
    assert page.locator('#drawer-error').evaluate('(e)=>e===document.activeElement')
    assert page.locator('#drawer').is_visible()
    assert page.locator('#transition').is_enabled()


@pytest.mark.parametrize('status', [401, 404, 503])
def test_missing_session_never_sends_mutation(board, status):
    page, state = board
    state['session'] = status
    request_transition(page)
    page.locator('#drawer-error').wait_for(state='visible')
    assert state['posts'] == []
    assert page.locator('#transition').is_enabled()


def test_issue_form_uses_authenticated_request(board):
    page, state = board
    page.locator('#new').click()
    page.locator('#issue-title').fill('Review session revocation')
    page.locator('#issue-form button[type=submit]').click()
    page.wait_for_function("document.querySelector('#toast').textContent==='Issue created in MAS-PM'")
    assert state['posts'][0]['body']['title'] == 'Review session revocation'
    assert state['posts'][0]['csrf'] == 'test-csrf'
    assert state['errors'] == []
