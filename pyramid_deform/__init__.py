import deform
import deform.form
import deform.exception
from deform.form import Button

from pyramid.httpexceptions import HTTPFound

class FormView(object):
    form_class = deform.form.Form
    buttons = ()
    schema = None

    def __init__(self, request):
        self.request = request

    def __call__(self):
        use_ajax = getattr(self, 'use_ajax', False)
        ajax_options = getattr(self, 'ajax_options', '')
        schema = self.schema.bind(request=self.request)
        form = self.form_class(schema, buttons=self.buttons, use_ajax=use_ajax,
                               ajax_options=ajax_options)
        self.before(form)
        reqts = form.get_widget_resources()
        result = None

        for button in form.buttons:
            if button.name in self.request.POST:
                success_method = getattr(self, '%s_success' % button.name)
                try:
                    controls = self.request.POST.items()
                    validated = form.validate(controls)
                    result = success_method(validated)
                except deform.exception.ValidationFailure, e:
                    fail = getattr(self, '%s_failure' % button.name, None)
                    if fail is None:
                        fail = self.failure
                    result = fail(e)
                break

        if result is None:
            result = self.show(form)

        if isinstance(result, dict):
            result['js_links'] = reqts['js']
            result['css_links'] = reqts['css']

        return result

    def before(self, form):
        pass

    def failure(self, e):
        return {
            'form':e.render(),
            }

    def show(self, form):
        return {
            'form':form.render(),
            }

class WizardState(object):
    def __init__(self, request, wizard_name):
        self.wizard_name = wizard_name
        self.request = request

    def _get_wizard_data(self):
        session = self.request.session
        wizdatas = session.setdefault('pyramid_deform.wizards', {})
        wizdata = wizdatas.get(self.wizard_name, None)
        if wizdata is None:
            wizdata = {}
            wizdatas[self.wizard_name] = wizdata
            session.changed()
        return wizdata

    def clear(self):
        wizdata = self._get_wizard_data()
        wizdata.clear()
        self.request.session.changed()

    def get_step_num(self):
        step = self.request.GET.get('step')
        if step is not None:
            step = int(step)
            self.set_step_num(step)
        else:
            wizdata = self._get_wizard_data()
            step = wizdata.get('step', 0)
        return int(step)

    def set_step_num(self, num):
        wizdata = self._get_wizard_data()
        wizdata['step'] = num
        self.request.session.changed()

    def get_step_states(self):
        wizdata = self._get_wizard_data()
        states = wizdata.setdefault('states', {})
        return states

    def get_step_state(self):
        states = self.get_step_states()
        step = self.get_step_num()
        return states.get(step, {})

    def set_step_state(self, num, name, state):
        states = self.get_step_states()
        states[num] = state
        states[name] = state
        self.request.session.changed()

    def decrement_step(self):
        step = self.get_step_num()
        if step > 0:
            self.set_step_num(step-1)

    def increment_step(self):
        step = self.get_step_num()
        self.set_step_num(step+1)

    def set_state(self, name, state):
        step = self.get_step_num()
        self.set_step_state(step, name, state)

class FormWizardView(object):

    form_view_class = FormView
    wizard_state_class = WizardState

    def __init__(self, wizard):
        self.wizard = wizard

    def __call__(self, request):
        self.request = request
        self.wizard_state = self.wizard_state_class(request, self.wizard.name)
        step = self.wizard_state.get_step_num()
        
        if step > len(self.wizard.schemas)-1:
            states = self.wizard_state.get_step_states()
            result = self.wizard.done(request, states)
            self.wizard_state.clear()
            return result
        form_view = self.form_view_class(request)
        schema = self.wizard.schemas[step]
        form_view.schema = schema
        self.schema_name = schema.name
        buttons = []
        if step > 0:
            buttons.append(Button(name='previous', title='Previous'))
        if step < len(self.wizard.schemas)-1:
            buttons.append(Button(name='next', title='Next'))
        else:
            buttons.append(Button(name='next', title='Done'))
        form_view.buttons = buttons
        form_view.next_success = self.next_success
        form_view.previous_success = self.previous_success
        form_view.previous_failure = self.previous_failure
        form_view.show = self.show
        result = form_view()
        return result

    def show(self, form):
        state = self.wizard_state.get_step_state()
        return {
            'form':form.render(appstruct=state)
            }

    def next_success(self, validated):
        self.wizard_state.set_state(self.schema_name, validated)
        self.wizard_state.increment_step()
        return HTTPFound(location = self.request.path_url)

    def previous_success(self, validated):
        self.wizard_state.set_state(self.schema_name, validated)
        self.wizard_state.decrement_step()
        return HTTPFound(location = self.request.path_url)

    def previous_failure(self, e):
        self.wizard_state.decrement_step()
        return HTTPFound(location = self.request.path_url)

class FormWizard(object):
    form_wizard_view_class = FormWizardView # for testing
    wizard_state_class = WizardState
    
    def __init__(self, name, done, *schemas):
        self.name = name
        self.schemas = schemas
        self.done = done

    def __call__(self, request):
        view = self.form_wizard_view_class(self)
        result = view(request)
        return result

    def get_summary(self, request):
        result = []
        for num, schema in enumerate(self.schemas):
            result.append({
                'num':num,
                'name':schema.name,
                'title':schema.title,
                'desc':schema.description,
                'url':request.path_url + '?step=%s' % num,
                })
        return result

