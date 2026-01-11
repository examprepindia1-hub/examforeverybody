from django.shortcuts import get_object_or_404
from django.views import View
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
from marketplace.models import MarketplaceItem
from mocktests.models import UserTestAttempt
from courses.models import UserCourseProgress
from .models import Certificate
from .services import generate_certificate_pdf

class DownloadCertificateView(LoginRequiredMixin, View):
    def get(self, request, slug):
        item = get_object_or_404(MarketplaceItem, slug=slug)
        user = request.user
        
        # 1. Eligibility Check
        can_download = False
        
        if item.item_type == MarketplaceItem.ItemType.MOCK_TEST:
            # Must have PASSED the test
            has_passed = UserTestAttempt.objects.filter(
                user=user, 
                test__item=item, 
                is_passed=True
            ).exists()
            if has_passed:
                can_download = True
                
        elif item.item_type == MarketplaceItem.ItemType.VIDEO_COURSE:
            # Must have COMPLETED the course (100%)
            progress = UserCourseProgress.objects.filter(
                user=user, 
                course__item=item, 
                is_completed=True
            ).exists()
            if progress:
                can_download = True
        
        if not can_download:
            return HttpResponseForbidden("You are not eligible for this certificate yet.")
            
        # 2. Get or Create Certificate
        certificate, created = Certificate.objects.get_or_create(user=user, item=item)
        
        # 3. Generate PDF
        pdf_bytes = generate_certificate_pdf(certificate)
        
        # 4. Return as Download
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Certificate-{item.slug}-{user.username}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

