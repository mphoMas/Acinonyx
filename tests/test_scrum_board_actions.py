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


def assert_expected_board(page, project_name, keys):
    """Acceptance must prove expected records, not merely a successful login."""
    assert page.locator('#project-name').inner_text() == project_name
    assert sorted(page.locator('[data-ticket]').evaluate_all('(nodes)=>nodes.map(n=>n.dataset.ticket)')) == sorted(keys)


def test_expected_board_records_and_empty_board_detection(board):
    page, _ = board
    assert_expected_board(page, 'Scrum Board Automation', ['SBA-5'])
    page.locator('[data-ticket="SBA-5"]').evaluate('(e)=>e.remove()')
    with pytest.raises(AssertionError):
        assert_expected_board(page, 'Scrum Board Automation', ['SBA-5'])


def test_missing_activity_identity_is_explicit(board):
    page, _ = board
    page.locator('[data-ticket="SBA-5"]').click()
    page.locator('#load-activity').click()
    assert 'integration is pending' in page.locator('#task-activity').inner_text()


def test_activity_summary_is_text_and_pass_is_not_trusted(board):
    page, _ = board
    page.route('**/api/pm/v1/tasks/task-1/activity?limit=100', lambda route: route.fulfill(json={'events': [{'kind': 'evidence.submitted', 'actor': 'agent', 'summary': '<img src=x onerror=alert(1)>', 'evidence': {'status': 'PASS', 'candidate_commit': 'abc'}}]}))
    page.locator('[data-ticket="SBA-5"]').click()
    page.evaluate("()=>loadTaskActivity({id:'task-1'})")
    assert page.locator('#task-activity').inner_text().find('Evidence: unverified') >= 0
    assert page.locator('#task-activity img').count() == 0


def test_login_structured_error_and_keyboard_feedback(board):
    page, _ = board
    page.route('**/portal/login.html', lambda route: route.fulfill(body=(ROOT / 'portal/login.html').read_text(), content_type='text/html'))
    page.route('**/api/pm/v1/session/login', lambda route: route.fulfill(status=401, json={'error': {'message': 'Credential expired'}}))
    page.goto('http://board.test/portal/login.html')
    page.locator('#tokenInput').fill('disposable-test-token')
    page.locator('#toggleToken').click()
    assert page.locator('#tokenInput').get_attribute('type') == 'text'
    page.locator('#submitBtn').click()
    page.locator('#errorAlert').wait_for(state='visible')
    assert page.locator('#errorAlert').inner_text() == 'Credential expired'
    assert page.locator('#errorAlert').evaluate('(e)=>e===document.activeElement')
    assert page.locator('#submitBtn').is_enabled()
    assert page.locator('#tokenInput').get_attribute('type') == 'password'


def load_workflow_fixture(page, payload, status=200):
    page.route('**/api/pm/v1/tasks/task-1/activity?limit=100',
               lambda route: route.fulfill(status=status, json=payload))
    page.locator('[data-ticket="SBA-5"]').click()
    page.evaluate("()=>loadTaskActivity({id:'task-1'})")


def test_empty_activity_attempts_and_reviews_are_explicit(board):
    page, _ = board
    load_workflow_fixture(page, {'events': [], 'attempts': [], 'reviews': []})
    assert 'No recorded activity' in page.locator('#task-activity').inner_text()
    assert 'No recorded attempts' in page.locator('#task-workflow').inner_text()
    assert 'No recorded reviews' in page.locator('#task-workflow').inner_text()


@pytest.mark.parametrize('status', [401, 403, 404, 503])
def test_workflow_error_remains_visible_and_retry_available(board, status):
    page, state = board
    load_workflow_fixture(page, {'error': {'message': 'Feed unavailable'}}, status)
    assert 'Activity unavailable' in page.locator('#task-activity').inner_text()
    assert 'Attempts and reviews unavailable' in page.locator('#task-workflow').inner_text()
    assert page.locator('#load-activity').is_enabled()
    assert page.locator('#task-activity').get_attribute('aria-busy') == 'false'
    assert state['posts'] == []


def test_uncertain_execution_and_pending_cancellation_do_not_imply_success(board):
    page, state = board
    load_workflow_fixture(page, {'events': [], 'attempts': [
        {'attempt_id': 'a1', 'state': 'UNKNOWN_EXECUTION'},
        {'attempt_id': 'a2', 'state': 'CANCEL_REQUESTED'},
        {'attempt_id': 'a3', 'state': 'SUCCEEDED'},
        {'attempt_id': 'a4', 'state': 'invented'},
    ]})
    text = page.locator('#task-workflow').inner_text()
    assert 'reconciliation required' in text
    assert 'stopping is not confirmed' in text
    assert 'verification still required' in text
    assert 'Unrecognized attempt state: invented' in text
    assert state['posts'] == []


def test_review_requires_current_candidate_trust_and_reviewer(board):
    page, _ = board
    load_workflow_fixture(page, {'events': [], 'current_candidate_commit': 'new', 'reviews': [
        {'review_id': 'old', 'decision': 'APPROVED', 'candidate_commit': 'old', 'trust_status': 'validated', 'reviewer_principal': 'critic'},
        {'review_id': 'claim', 'decision': 'APPROVED', 'candidate_commit': 'new', 'trust_status': 'claimed', 'reviewer_principal': 'agent'},
        {'review_id': 'reject', 'decision': 'REJECTED', 'candidate_commit': 'new', 'trust_status': 'validated', 'reviewer_principal': 'critic'},
        {'review_id': 'approve', 'decision': 'APPROVED', 'candidate_commit': 'new', 'trust_status': 'validated', 'reviewer_principal': 'critic'},
    ]})
    text = page.locator('#task-workflow').inner_text()
    assert 'Stale review' in text
    assert 'Unverified review claim' in text
    assert 'Validated rejection' in text
    assert 'release authorization is separate' in text


def test_workflow_fields_are_plain_text_on_narrow_viewport(board):
    page, _ = board
    page.set_viewport_size({'width': 390, 'height': 844})
    load_workflow_fixture(page, {'events': [], 'attempts': [
        {'attempt_id': '<img src=x onerror=alert(1)>', 'state': 'RUNNING'}], 'reviews': []})
    assert '<img src=x' in page.locator('#task-workflow').inner_text()
    assert page.locator('#task-workflow img').count() == 0
    assert page.locator('#load-activity').is_visible()


@pytest.mark.parametrize('payload', [{'events': [] , 'attempts': {}}, {'events': [None]}, {'events': [], 'reviews': [None]}])
def test_malformed_workflow_is_error_not_empty_success(board, payload):
    page, _ = board
    load_workflow_fixture(page, payload)
    assert 'unavailable or unsupported' in page.locator('#task-activity').inner_text()


def test_delayed_activity_cannot_replace_new_drawer(board):
    page, _ = board
    pending = []
    page.route('**/api/pm/v1/tasks/task-1/activity?limit=100', lambda route: pending.append(route))
    page.locator('[data-ticket="SBA-5"]').click()
    page.evaluate("()=>{void loadTaskActivity({id:'task-1'})}")
    page.wait_for_function("document.querySelector('#task-activity').getAttribute('aria-busy')==='true'")
    page.wait_for_timeout(100)
    assert pending
    page.locator('#close-drawer').click()
    page.locator('[data-ticket="SBA-5"]').click()
    pending[0].fulfill(json={'events': [{'summary': 'OLD RESPONSE'}], 'attempts': [], 'reviews': []})
    page.wait_for_timeout(100)
    assert page.locator('#task-activity').inner_text() == 'No activity requested.'
    assert page.locator('#task-workflow').inner_text() == 'No attempt or review data requested.'
