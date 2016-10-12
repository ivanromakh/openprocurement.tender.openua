# -*- coding: utf-8 -*-
from openprocurement.api.utils import (
    save_tender,
    upload_file,
    apply_patch,
    update_file_content_type,
    opresource,
    json_view,
    context_unpack,
)
from openprocurement.api.validation import (
    validate_file_update,
    validate_file_upload,
    validate_patch_document_data,
)
from openprocurement.api.views.complaint_document import TenderComplaintDocumentResource


STATUS4ROLE = {
    'complaint_owner': ['draft', 'answered', 'claim', 'pending', 'accepted', 'satisfied'],
    'aboveThresholdReviewers': ['pending', 'accepted', 'stopping'],
    'tender_owner': ['claim', 'pending', 'accepted', 'satisfied'],
}


@opresource(name='Tender UA Complaint Documents',
            collection_path='/tenders/{tender_id}/complaints/{complaint_id}/documents',
            path='/tenders/{tender_id}/complaints/{complaint_id}/documents/{document_id}',
            procurementMethodType='aboveThresholdUA',
            description="Tender complaint documents")
class TenderUaComplaintDocumentResource(TenderComplaintDocumentResource):

    def validate_complaint_document(self, operation):
        if operation == 'update' and self.request.authenticated_role != self.context.author:
            self.request.errors.add('url', 'role', 'Can update document only author')
            self.request.errors.status = 403
            return
        if self.request.validated['tender_status'] not in ['active.tendering']:
            self.request.errors.add('body', 'data', 'Can\'t {} document in current ({}) tender status'.format(operation, self.request.validated['tender_status']))
            self.request.errors.status = 403
            return
        if self.request.validated['complaint'].status not in STATUS4ROLE.get(self.request.authenticated_role, []):
            self.request.errors.add('body', 'data', 'Can\'t {} document in current ({}) complaint status'.format(operation, self.request.validated['complaint'].status))
            self.request.errors.status = 403
            return
        return True

    @json_view(validators=(validate_file_upload,), permission='edit_complaint')
    def collection_post(self):
        """Tender Complaint Document Upload
        """
        if not self.validate_complaint_document('add'):
            return
        document = upload_file(self.request)
        document.author = self.request.authenticated_role
        self.context.documents.append(document)
        if save_tender(self.request):
            self.LOGGER.info('Created tender complaint document {}'.format(document.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_complaint_document_create'}, {'document_id': document.id}))
            self.request.response.status = 201
            document_route = self.request.matched_route.name.replace("collection_", "")
            self.request.response.headers['Location'] = self.request.current_route_url(_route_name=document_route, document_id=document.id, _query={})
            return {'data': document.serialize("view")}

    @json_view(validators=(validate_file_update,), permission='edit_complaint')
    def put(self):
        """Tender Complaint Document Update"""
        if not self.validate_complaint_document('update'):
            return
        document = upload_file(self.request)
        document.author = self.request.authenticated_role
        self.request.validated['complaint'].documents.append(document)
        if save_tender(self.request):
            self.LOGGER.info('Updated tender complaint document {}'.format(self.request.context.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_complaint_document_put'}))
            return {'data': document.serialize("view")}

    @json_view(content_type="application/json", validators=(validate_patch_document_data,), permission='edit_complaint')
    def patch(self):
        """Tender Complaint Document Update"""
        if not self.validate_complaint_document('update'):
            return
        if apply_patch(self.request, src=self.request.context.serialize()):
            update_file_content_type(self.request)
            self.LOGGER.info('Updated tender complaint document {}'.format(self.request.context.id),
                        extra=context_unpack(self.request, {'MESSAGE_ID': 'tender_complaint_document_patch'}))
            return {'data': self.request.context.serialize("view")}
