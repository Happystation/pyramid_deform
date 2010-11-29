import unittest
from pyramid import testing

class TestFormView(unittest.TestCase):
    def _getTargetClass(self):
        from pyramid_deform import FormView
        return FormView
        
    def _makeOne(self, request):
        klass = self._getTargetClass()
        inst = klass(request)
        return inst

    def test___call__show(self):
        schema = DummySchema()
        request = DummyRequest()
        inst = self._makeOne(request)
        inst.schema = schema
        inst.form_class = DummyForm
        result = inst()
        self.assertEqual(result,
                         {'css_links': (), 'js_links': (), 'form': 'rendered'})

    def test___call__show_result_response(self):
        from webob import Response
        schema = DummySchema()
        request = DummyRequest()
        inst = self._makeOne(request)
        inst.schema = schema
        inst.form_class = DummyForm
        response = Response()
        inst.show = lambda *arg: response
        result = inst()
        self.assertEqual(result, response)

    def test___call__button_in_request(self):
        schema = DummySchema()
        request = DummyRequest()
        request.POST['submit'] = True
        inst = self._makeOne(request)
        inst.schema = schema
        inst.buttons = (DummyButton('submit'), )
        inst.submit_success = lambda *x: 'success'
        inst.form_class = DummyForm
        result = inst()
        self.assertEqual(result, 'success')
        
    def test___call__button_in_request_fail(self):
        schema = DummySchema()
        request = DummyRequest()
        request.POST['submit'] = True
        inst = self._makeOne(request)
        inst.schema = schema
        inst.buttons = (DummyButton('submit'), )
        import deform.exception
        def raiseit(*arg):
            raise deform.exception.ValidationFailure(None, None, None)
        inst.submit_success = raiseit
        inst.form_class = DummyForm
        inst.submit_failure = lambda *arg: 'failure'
        result = inst()
        self.assertEqual(result, 'failure')

    def test___call__button_in_request_fail_no_failure_handler(self):
        schema = DummySchema()
        request = DummyRequest()
        request.POST['submit'] = True
        inst = self._makeOne(request)
        inst.schema = schema
        inst.buttons = (DummyButton('submit'), )
        import deform.exception
        def raiseit(*arg):
            exc = deform.exception.ValidationFailure(None, None, None)
            exc.render = lambda *arg: 'failure'
            raise exc
        inst.submit_success = raiseit
        inst.form_class = DummyForm
        result = inst()
        self.assertEqual(result,
                         {'css_links': (), 'js_links': (), 'form': 'failure'})

class TestFormWizardView(unittest.TestCase):
    def _makeOne(self, wizard):
        from pyramid_deform import FormWizardView
        return FormWizardView(wizard)

    def test___call__step_zero_no_schemas(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result, 'done')

    def test___call__step_zero_one_schema(self):
        schema = DummySchema()
        wizard = DummyFormWizard(schema)
        inst = self._makeOne(wizard)
        inst.form_view_class = DummyFormView
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result, 'viewed')

    def test_show(self):
        form = DummyForm(None)
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        inst.request = DummyRequest()
        result = inst.show(form)
        self.assertEqual(result, {'form': 'rendered'})
        self.assertEqual(form.appstruct, {})

    def test_next_success(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        result = inst.next_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['step'], 1)
        self.assertEqual(state['states'][0], {'one':'one'})

    def test_previous_success_at_step_zero(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        result = inst.previous_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['states'][0], {'one':'one'})
        self.failIf('step' in state)

    def test_previous_success_at_step_one(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        states = inst.request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'step':1}
        result = inst.previous_success({'one':'one'})
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['states'][1], {'one':'one'})
        self.assertEqual(state['step'], 0)

    def test_previous_failure_at_step_zero(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        result = inst.previous_failure(None)
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.failIf('step' in state)

    def test_previous_failure_at_step_one(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        states = inst.request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'step':1}
        result = inst.previous_failure(None)
        self.assertEqual(result.status, '302 Found')
        self.assertEqual(result.location, 'http://example.com')
        state = request.session['pyramid_deform.wizards']['name']
        self.assertEqual(state['step'], 0)

    def test__get_wizard_data_no_existing_data(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        data = inst._get_wizard_data()
        self.assertEqual(data, {})
        self.failUnless('name' in request.session['pyramid_deform.wizards'])
        self.failUnless(request.session._changed)

    def test__get_wizard_data_with_existing_data(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        state = {'abc':'123'}
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = state
        inst.request = request
        data = inst._get_wizard_data()
        self.assertEqual(data, state)
        self.failIf(request.session._changed)

    def test_clear_wizard_data(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        state = {'abc':'123'}
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = state
        inst.request = request
        inst.clear_wizard_data()
        self.assertEqual(request.session['pyramid_deform.wizards']['name'], {})

    def test_clear_get_step_num_from_params(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        request.GET['step'] = '1'
        inst.request = request
        self.assertEqual(inst.get_step_num(), 1)

    def test_clear_get_step_num_from_session(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'step':'1'}
        inst.request = request
        self.assertEqual(inst.get_step_num(), 1)

    def test_set_step_num(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        inst.request = request
        inst.set_step_num(5)
        self.assertEqual(inst.get_step_num(), 5)

    def test_get_step_states(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'states':'states', 'step':0}
        inst.request = request
        self.assertEqual(inst.get_step_states(), 'states')

    def test_get_step_state(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'states':{0:'state'}, 'step':0}
        inst.request = request
        self.assertEqual(inst.get_step_state(), 'state')

    def test_set_step_state(self):
        wizard = DummyFormWizard()
        inst = self._makeOne(wizard)
        request = DummyRequest()
        states = request.session['pyramid_deform.wizards'] = {}
        states['name'] = {'states':{0:'state'}, 'step':0}
        inst.request = request
        inst.set_step_state(0, 'state2')
        self.assertEqual(states['name']['states'][0], 'state2')

class TestFormWizard(unittest.TestCase):
    def _makeOne(self, name, done, *schemas):
        from pyramid_deform import FormWizard
        return FormWizard(name, done, *schemas)
    
    def test___call__(self):
        inst = self._makeOne('name', None, 'schema1', 'schema2')
        inst.form_wizard_view_class = DummyFormWizardView
        request = DummyRequest()
        result = inst(request)
        self.assertEqual(result.wizard, inst)

    def test_done_name_in_wizdata(self):
        def done(request, validated):
            return validated
        inst = self._makeOne('name', done, 'schema1', 'schema2')
        request = DummyRequest()
        wizdata = {'foo':1}
        data = request.session['pyramid_deform.wizards'] = {}
        data['name'] = wizdata
        validated = 'abc'
        result = inst.done(request, validated)
        self.assertEqual(result, validated)
        self.assertEqual(data, {})
        self.failUnless(request.session._changed)

    def test_done_name_not_in_wizdata(self):
        def done(request, validated):
            return validated
        inst = self._makeOne('name', done, 'schema1', 'schema2')
        request = DummyRequest()
        data = request.session['pyramid_deform.wizards'] = {}
        validated = 'abc'
        result = inst.done(request, validated)
        self.assertEqual(result, validated)
        self.assertEqual(data, {})
        self.failIf(request.session._changed)

class DummyForm(object):
    def __init__(self, schema, buttons=None, use_ajax=False, ajax_options=''):
        self.schema = schema
        self.buttons = buttons
        self.use_ajax = use_ajax
        self.ajax_options = ajax_options

    def get_widget_resources(self):
        return {'js':(), 'css':()}

    def render(self, appstruct=None):
        self.appstruct = appstruct
        return 'rendered'

    def validate(self, controls):
        return 'validated'

class DummySchema(object):
    def bind(self, **kw):
        self.kw = kw
        return self
    
class DummyButton(object):
    def __init__(self, name):
        self.name = name
        
class DummyFormWizardView(object):
    def __init__(self, wizard):
        self.wizard = wizard

    def __call__(self, request):
        return self
    
class DummyFormWizard(object):
    name = 'name'
    def __init__(self, *schemas):
        self.schemas = schemas

    def done(self, request, states):
        return 'done'

class DummySession(dict):
    _changed = False
    def changed(self):
        self._changed = True

class DummyRequest(testing.DummyRequest):
    def __init__(self, *arg, **kw):
        testing.DummyRequest.__init__(self, *arg, **kw)
        self.session = DummySession()
    
class DummyFormView(object):
    def __init__(self, request):
        self.request = request

    def __call__(self):
        return 'viewed'
        

