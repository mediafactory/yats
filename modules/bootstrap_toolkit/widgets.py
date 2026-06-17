from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape


def add_to_css_class(classes, new_class):
    new_class = new_class.strip()
    if new_class:
        # Turn string into list of classes
        classes = classes.split(" ")
        # Strip whitespace
        classes = [c.strip() for c in classes]
        # Remove empty elements
        classes = filter(None, classes)
        # Test for existing
        if not new_class in classes:
            classes.append(new_class)
            # Convert to string
        classes = u' '.join(classes)
    return classes


def create_prepend_append(**kwargs):
    bootstrap = {}
    bootstrap['append'] = kwargs.pop('append', None)
    bootstrap['prepend'] = kwargs.pop('prepend', None)
    return bootstrap, kwargs


class BootstrapUneditableInput(forms.TextInput):

    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        attrs['type'] = 'hidden'
        klass = add_to_css_class(self.attrs.pop('class', ''), 'uneditable-input')
        klass = add_to_css_class(klass, attrs.pop('class', ''))
        base = super(BootstrapUneditableInput, self).render(name, value, attrs)
        return mark_safe(base + u'<span class="%s">%s</span>' % (klass, conditional_escape(value)))


class BootstrapTextInput(forms.TextInput):

    def __init__(self, *args, **kwargs):
        self.bootstrap, kwargs = create_prepend_append(**kwargs)
        super(BootstrapTextInput, self).__init__(*args, **kwargs)


class BootstrapPasswordInput(forms.PasswordInput):

    def __init__(self, *args, **kwargs):
        self.bootstrap, kwargs = create_prepend_append(**kwargs)
        super(BootstrapPasswordInput, self).__init__(*args, **kwargs)


class BootstrapDateInput(forms.DateInput):
    """Native HTML5 date picker (replaces the old bootstrap-datepicker)."""

    bootstrap = {'append': None, 'prepend': None}
    input_type = 'date'  # native <input type=date> needs ISO format on the wire

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format='%Y-%m-%d')


class BootstrapDateTimeInput(forms.DateTimeInput):
    """Native HTML5 datetime picker (replaces the old bootstrap-datetimepicker)."""

    bootstrap = {'append': None, 'prepend': None}
    input_type = 'datetime-local'

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format='%Y-%m-%dT%H:%M')
