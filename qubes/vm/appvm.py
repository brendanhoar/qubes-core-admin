#!/usr/bin/python2 -O
# vim: fileencoding=utf-8

import qubes.events
import qubes.vm.qubesvm
from qubes.config import defaults


class AppVM(qubes.vm.qubesvm.QubesVM):
    '''Application VM'''

    template = qubes.VMProperty('template',
                                load_stage=4,
                                vmclass=qubes.vm.templatevm.TemplateVM,
                                ls_width=31,
                                doc='Template, on which this AppVM is based.')

    def __init__(self, *args, **kwargs):
        self.volumes = {}
        self.volume_config = {
            'root': {
                'name': 'root',
                'pool': 'default',
                'volume_type': 'snapshot',
            },
            'private': {
                'name': 'private',
                'pool': 'default',
                'volume_type': 'read-write',
                'size': defaults['private_img_size'],
            },
            'volatile': {
                'name': 'volatile',
                'pool': 'default',
                'volume_type': 'volatile',
                'size': defaults['root_img_size'],
            },
            'kernel': {
                'name': 'kernel',
                'pool': 'linux-kernel',
                'volume_type': 'read-only',
            }
        }
        super(AppVM, self).__init__(*args, **kwargs)

    @qubes.events.handler('domain-load')
    def on_domain_loaded(self, event):
        # pylint: disable=unused-argument
        # Some additional checks for template based VM
        assert self.template
        # self.template.appvms.add(self) # XXX