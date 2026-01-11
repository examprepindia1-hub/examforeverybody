from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from marketplace.models import MarketplaceItem
from mocktests.models import MockTestAttributes, UserTestAttempt
from courses.models import CourseAttributes, UserCourseProgress
from certificates.models import Certificate
import datetime

User = get_user_model()

class CertificateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student', email='student@test.com', password='password')
        self.client.login(email='student@test.com', password='password')
        
        # 1. Mock Test Setup
        self.test_item = MarketplaceItem.objects.create(title="Mock Test 1", slug="mock-test-1", item_type="MOCK_TEST", is_active=True, price=10)
        self.test_attr = MockTestAttributes.objects.create(item=self.test_item, duration_minutes=60, pass_percentage=50)

        # 2. Course Setup
        self.course_item = MarketplaceItem.objects.create(title="Video Course 1", slug="video-course-1", item_type="VIDEO_COURSE", is_active=True, price=10)
        self.course_attr = CourseAttributes.objects.create(item=self.course_item)

    def test_mock_test_certificate_access(self):
        url = reverse('certificates:download', kwargs={'slug': self.test_item.slug})
        
        # A. Attempt Failed
        UserTestAttempt.objects.create(user=self.user, test=self.test_attr, score=40, is_passed=False)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403) # Forbidden
        
        # B. Attempt Passed
        UserTestAttempt.objects.create(user=self.user, test=self.test_attr, score=80, is_passed=True)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        
        # Check Certificate Created
        self.assertTrue(Certificate.objects.filter(user=self.user, item=self.test_item).exists())

    def test_course_certificate_access(self):
        url = reverse('certificates:download', kwargs={'slug': self.course_item.slug})
        
        # A. Incomplete
        UserCourseProgress.objects.create(user=self.user, course=self.course_attr, percent_complete=50.0, is_completed=False)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        
        # B. Complete
        UserCourseProgress.objects.filter(user=self.user, course=self.course_attr).update(percent_complete=100.0, is_completed=True)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
