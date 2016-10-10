import os
import traceback

from DateTime import DateTime
from Products.ATContentTypes.lib import constraintypes
from Products.Archetypes.public import BaseFolder
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import _createObjectByType
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.app.content.browser.interfaces import IFolderContentsView
from plone.app.layout.globals.interfaces import IViewView
from zope.interface import implements

from bika.lims.browser import BrowserView
from bika.lims.browser.bika_listing import BikaListingView
from bika.lims.browser.multifile import MultifileView
from bika.lims.utils import to_utf8
from bika.sanbi import bikaMessageFactory as _


class ShipmentView(BikaListingView):
    template = ViewPageTemplateFile('templates/shipment_view.pt')

    def __init__(self, context, request):
        super(ShipmentView, self).__init__(context, request)
        self.context = context
        self.request = request

    def __call__(self):
        self.absolute_url = self.context.absolute_url()
        self.id = self.context.getId()
        self.title = self.context.Title()
        self.study_name = self.context.aq_parent.Title()
        self.from_contact = self.context.getFromContact()
        self.to_contact = self.context.getToContact().Title()
        self.sender_address = self.context.getDeliveryAddress()
        self.courier_name = self.context.getCourier()
        uids = [kit.UID() for kit in self.context.getKits()]
        Kits = ShipmentKitsView(self.context, self.request, uids)
        self.kits_table = Kits.contents_table(table_only=True)

        return self.template()

class ShipmentKitsView(BikaListingView):

    implements(IFolderContentsView, IViewView)

    def __init__(self, context, request, kit_uids):
        super(ShipmentKitsView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.uids = kit_uids
        self.catalog = 'bika_catalog'
        path = path = '/'.join(context.aq_parent.getPhysicalPath())
        self.contentFilter = {
            'portal_type': 'Kit',
            'UID': self.uids,
            'sort_on': 'sortable_title',
            'path': {'query': path, 'depth': 1, 'level': 0}
        }
        self.context_actions = {}
        self.title = ''
        self.description = ''
        self.icon = ''
        self.show_sort_column = False
        self.show_select_row = False
        self.show_select_column = False
        self.show_column_toggles = False
        self.context_actions = {}
        self.allow_edit = False
        self.pagesize = 999999
        self.columns = {
            'Title': {'title': _('Kit Name'),
                      'index': 'sortable_title'},
            'kitTemplate': {'title': _('Kit template'),
                            'toggle': True},
            'state_title': {'title': _('State'),
                            'index': 'review_state'},
        }

        self.review_states = [
            {
                'id': 'default',
                'title': _('All'),
                'contentFilter': {'sort_on': 'created',
                                  'sort_order': 'ascending'},
                'transitions': [],
                'columns': [
                    'Title',
                    'kitTemplate',
                    'state_title'
                ]
            }
        ]

    def folderitem(self, obj, item, index):
        if not item.has_key('obj'):
            return item
        obj = item['obj']
        item['kitTemplate'] = obj.getKitTemplate().Title()
        item['replace']['Title'] = "<a href='%s'>%s</a>" % \
                                    (item['url'], obj.title)
        item['replace']['kitTemplate'] = "<a href='%s'>%s</a>" % \
                                         (obj.getKitTemplate().absolute_url(), obj.getKitTemplate().Title())
        return item


class EditView(BrowserView):
    template = ViewPageTemplateFile('templates/shipment_edit.pt')
    # field = ViewPageTemplateFile('templates/row_field.pt')

    def __call__(self):
        portal = self.portal
        request = self.request
        context = self.context
        setup = portal.bika_setup

        if 'submitted' in request:
            # pdb.set_trace()
            context.setConstrainTypesMode(constraintypes.DISABLED)
            # This following line does the same as precedent which one is the
            #  best?

            # context.aq_parent.setConstrainTypesMode(constraintypes.DISABLED)
            portal_factory = getToolByName(context, 'portal_factory')
            context = portal_factory.doCreate(context, context.id)
            context.processForm()

            obj_url = context.absolute_url_path()
            request.response.redirect(obj_url)
            return

        return self.template()

    def get_fields_with_visibility(self, visibility, mode=None):
        mode = mode if mode else 'edit'
        schema = self.context.Schema()
        fields = []
        for field in schema.fields():
            isVisible = field.widget.isVisible
            v = isVisible(self.context, mode, default='invisible', field=field)
            if v == visibility:
                fields.append(field)
        return fields

class ShipmentMultifileView(MultifileView):
    implements(IFolderContentsView, IViewView)

    def __init__(self, context, request):
        super(ShipmentMultifileView, self).__init__(context, request)
        self.show_workflow_action_buttons = False
        self.title = self.context.translate(_("Shipment Files"))
        self.description = "Different interesting documents and files to be attached to the shipment"

class PrintView(ShipmentView):
    template = ViewPageTemplateFile('templates/print.pt')
    _TEMPLATES_DIR = 'templates/print'

    def __call__(self):

        context = self.context
        portal = self.portal

        self.absolute_url = context.absolute_url()
        setup = portal.bika_setup
        # Disable the add new menu item
        # context.setConstrainTypesMode(1)
        # context.setLocallyAllowedTypes(())
        # Collect general data
        self.id = context.getId()
        self.title = context.Title()
        self.sender_address = context.getDeliveryAddress()
        self.header_text = "{0} : {1}".format(context.aq_parent,
                                              context.aq_parent.getId())
        self.from_contact = context.getFromContact()
        self.to_contact = context.getToContact().Title()
        self.study_name = context.aq_parent.Title()
        kits = context.getKits()
        kit_template = kits[0].getKitTemplate()
        self.kit_name = kit_template.Title()
        self.kit_quantity = len(kits)
        # self.kit_assembled_date = kit.CreationDate()
        # self.kit_expiration_date = self.ulocalized_time(kit.getExpiryDate())

        self.date_dispatched = self.ulocalized_time(context.getDateDispatched())
        self.courier_name = context.getCourier()

        self.user = context.getOwner()

        return self.template()

    def getCSS(self):
        template_name = 'shipment_print.pt'
        this_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(this_dir, self._TEMPLATES_DIR)
        path = '%s/%s.css' % (templates_dir, template_name[:-3])
        with open(path, 'r') as content_file:
            content = content_file.read()

        return content

    def render_shipment(self):
        templates_dir = self._TEMPLATES_DIR
        template_name = 'shipment_print.pt'
        self.header_text = "{0} : {1}".format(self.context.aq_parent,
                                              self.context.aq_parent.getId())
        embed = ViewPageTemplateFile(os.path.join(templates_dir, template_name))
        reptemplate = ""
        try:
            reptemplate = embed(self)
        except:
            tbex = traceback.format_exc()
            ktid = self.context.id
            reptemplate = "<div class='error-print'>%s - %s " \
                          "'%s':<pre>%s</pre></div>" % (
                ktid, _("Unable to load the template"), template_name, tbex)

        return reptemplate

    def _createdby_data(self):
        """ Returns a dict that represents the user who created the ws
            Keys: username, fullmame, email
        """
        username = self.context.getOwner().getUserName()
        return {'username': username,
                'fullname': to_utf8(self.user_fullname(username)),
                'email': to_utf8(self.user_email(username))}

    def _printedby_data(self):
        """ Returns a dict that represents the user who prints the ws
            Keys: username, fullname, email
        """
        data = {}
        member = self.context.portal_membership.getAuthenticatedMember()
        if member:
            username = member.getUserName()
            data['username'] = username
            data['fullname'] = to_utf8(self.user_fullname(username))
            data['email'] = to_utf8(self.user_email(username))

            c = [x for x in self.bika_setup_catalog(portal_type='LabContact')
                 if x.getObject().getUsername() == username]
            if c:
                sf = c[0].getObject().getSignature()
                if sf:
                    data['signature'] = sf.absolute_url() + "/Signature"

        return data

    def _lab_data(self):
        """ Returns a dictionary that represents the lab object
            Keys: obj, title, url, address, confidence, accredited,
                  accreditation_body, accreditation_logo, logo
        """
        portal = self.context.portal_url.getPortalObject()
        lab = self.context.bika_setup.laboratory
        lab_address = lab.getPostalAddress() \
                      or lab.getBillingAddress() \
                      or lab.getPhysicalAddress()
        if lab_address:
            _keys = ['address', 'city', 'state', 'zip', 'country']
            _list = ["<div>%s</div>" % lab_address.get(v) for v in _keys
                     if lab_address.get(v)]
            lab_address = "".join(_list)
        else:
            lab_address = ''

        return {'obj': lab,
                'title': to_utf8(lab.Title()),
                'url': to_utf8(lab.getLabURL()),
                'address': to_utf8(lab_address),
                'confidence': lab.getConfidence(),
                'accredited': lab.getLaboratoryAccredited(),
                'accreditation_body': to_utf8(lab.getAccreditationBody()),
                'accreditation_logo': lab.getAccreditationBodyLogo(),
                'logo': "%s/logo_print.png" % portal.absolute_url()}

    def getKitInfo(self):
        data = {
            'date_printed': self.ulocalized_time(DateTime(), long_format=1),
            'date_created': self.ulocalized_time(self.context.created(),
                                                 long_format=1),
        }
        data['createdby'] = self._createdby_data()
        data['printedby'] = self._printedby_data()
        data['laboratory'] = self._lab_data()

        return data
