from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from marketplace.models import MarketplaceItem
from enrollments.models import UserEnrollment
from courses.models import CourseAttributes, CourseModule, CourseLesson, UserCourseProgress, UserLessonCompletion
import json

User = get_user_model()

class CourseProgressTests(TestCase):
    def setUp(self):
        # 1. Create User
        self.user = User.objects.create_user(username='student', email='student@test.com', password='password')
        self.client.login(email='student@test.com', password='password')
        
        # 2. Create Course Structure
        self.item = MarketplaceItem.objects.create(title="Test Course", slug="test-course", item_type="VIDEO_COURSE", is_active=True, price=10)
        self.course_attr = CourseAttributes.objects.create(item=self.item)
        self.module = CourseModule.objects.create(course=self.course_attr, title="Module 1")
        self.lesson1 = CourseLesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.lesson2 = CourseLesson.objects.create(module=self.module, title="Lesson 2", order=2)
        
        # 3. Enroll User
        UserEnrollment.objects.create(user=self.user, item=self.item)

    def test_toggle_completion_api(self):
        url = reverse('courses:toggle_lesson_completion')
        
        # A. Mark Lesson 1 as Complete
        response = self.client.post(url, json.dumps({'lesson_id': self.lesson1.id}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['is_completed'])
        self.assertEqual(data['percent_complete'], 50.0) # 1 out of 2 = 50%
        
        # Verify DB
        self.assertTrue(UserLessonCompletion.objects.filter(user=self.user, lesson=self.lesson1).exists())
        self.assertEqual(UserCourseProgress.objects.get(user=self.user, course=self.course_attr).percent_complete, 50.0)

        # B. Mark Lesson 2 as Complete (Should be 100%)
        response = self.client.post(url, json.dumps({'lesson_id': self.lesson2.id}), content_type='application/json')
        data = response.json()
        self.assertEqual(data['percent_complete'], 100.0)
        self.assertTrue(UserCourseProgress.objects.get(user=self.user, course=self.course_attr).is_completed)

        # C. Toggle Lesson 1 OFF (Should go back to 50%)
        response = self.client.post(url, json.dumps({'lesson_id': self.lesson1.id}), content_type='application/json')
        data = response.json()
        self.assertFalse(data['is_completed'])
        self.assertEqual(data['percent_complete'], 50.0)
