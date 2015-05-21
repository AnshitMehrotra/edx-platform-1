"""
This file includes the tests for bookmark views.
"""

import json

from django.core.urlresolvers import reverse
from rest_framework.test import APIClient

from student.tests.factories import UserFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory

from .factories import BookmarkFactory

# pylint: disable=no-member


class BookmarksViewTestsMixin(ModuleStoreTestCase):
    """
    Mixin for bookmark view tests.
    """
    test_password = "test"

    def setUp(self):
        super(BookmarksViewTestsMixin, self).setUp()

        self.anonymous_client = APIClient()
        self.user = UserFactory.create(password=self.test_password)
        self.create_test_data()
        self.client = self.login_client(user=self.user)

    def login_client(self, user):
        """
        Helper method for getting the client and user and logging in. Returns client.
        """
        client = APIClient()
        client.login(username=user.username, password=self.test_password)
        return client

    def create_test_data(self):
        """
        Creates the bookmarks test data.
        """
        self.course = CourseFactory.create(display_name='An Introduction to API Testing')
        self.course_id = unicode(self.course.id)

        chapter_1 = ItemFactory.create(
            parent_location=self.course.location, category='chapter', display_name="Week 1"
        )
        sequential_1 = ItemFactory.create(
            parent_location=chapter_1.location, category='sequential', display_name="Lesson 1"
        )
        vertical_1 = ItemFactory.create(
            parent_location=sequential_1.location, category='vertical', display_name='Subsection 1'
        )
        self.video_1 = ItemFactory.create(
            parent_location=vertical_1.location, category="video", display_name="1st bookmarked Video"
        )
        self.bookmark_1 = BookmarkFactory.create(
            user=self.user,
            course_key=self.course_id,
            usage_key=self.video_1.location,
            display_name=self.video_1.display_name
        )

        chapter_2 = ItemFactory.create(
            parent_location=self.course.location, category='chapter', display_name="Week 2"
        )
        sequential_2 = ItemFactory.create(
            parent_location=chapter_2.location, category='sequential', display_name="Lesson 1"
        )
        vertical_2 = ItemFactory.create(
            parent_location=sequential_2.location, category='vertical', display_name='Subsection 1'
        )
        video2 = ItemFactory.create(
            parent_location=vertical_2.location, category="video", display_name="2nd bookmarked Video"
        )
        self.video_3 = ItemFactory.create(
            parent_location=vertical_2.location, category="video", display_name="3rd bookmarked Video"
        )
        self.bookmark_2 = BookmarkFactory.create(
            user=self.user,
            course_key=self.course_id,
            usage_key=video2.location,
            display_name=video2.display_name
        )

    def assert_valid_bookmark_response(self, response_data, bookmark, optional_fields=False):
        """
        Determines if the given response data (dict) matches the specified bookmark.
        """
        self.assertEqual(response_data['id'], "%s,%s" % (self.user.username, unicode(bookmark.usage_key)))
        self.assertEqual(response_data['usage_id'], unicode(bookmark.usage_key))
        self.assertEqual(response_data['course_id'], unicode(bookmark.course_key))
        self.assertIsNotNone(response_data["created"])

        if optional_fields:
            self.assertEqual(response_data['path'], bookmark.path)
            self.assertEqual(response_data['display_name'], bookmark.display_name)

    def send_get(self, client, url, query_parameters=None, expected_status=200):
        """
        Helper method for sending a GET to the server. Verifies the expected status and returns the response.
        """
        url = url + '?' + query_parameters if query_parameters else url
        response = client.get(url)
        self.assertEqual(expected_status, response.status_code)
        return response

    def send_post(self, client, url, json_data, content_type="application/json", expected_status=201):
        """
        Helper method for sending a POST to the server. Verifies the expected status and returns the response.
        """
        url = url + '?course_id={}'.format(self.course_id)
        response = client.post(url, data=json.dumps(json_data), content_type=content_type)
        self.assertEqual(expected_status, response.status_code)
        return response

    def send_delete(self, client, url, expected_status=204):
        """
        Helper method for sending a DELETE to the server. Verifies the expected status and returns the response.
        """
        response = client.delete(url)
        self.assertEqual(expected_status, response.status_code)
        return response


class BookmarksViewTests(BookmarksViewTestsMixin):
    """
    This contains the tests for GET & POST methods of bookmark.views.BookmarksView class
    GET /api/bookmarks/v0/bookmarks/?course_id={course_id1}
    POST /api/bookmarks/v0/bookmarks/?course_id={course_id1}
    """

    def test_get_bookmarks_successfully(self):
        """
        Test that requesting bookmarks for a course returns records successfully in
        expected order without optional fields.
        """
        query_parameters = 'course_id={}'.format(self.course_id)
        response = self.send_get(client=self.client, url=reverse('bookmarks'), query_parameters=query_parameters)

        bookmarks = response.data['results']

        self.assertEqual(len(bookmarks), 2)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['num_pages'], 1)

        # As bookmarks are sorted by -created so we will compare in that order.
        self.assert_valid_bookmark_response(bookmarks[0], self.bookmark_2)
        self.assert_valid_bookmark_response(bookmarks[1], self.bookmark_1)

    def test_get_bookmarks_with_optional_fields(self):
        """
        Test that requesting bookmarks for a course returns records successfully in
        expected order with optional fields.
        """
        query_parameters = 'course_id={}&fields=path,display_name'.format(self.course_id)

        response = self.send_get(client=self.client, url=reverse('bookmarks'), query_parameters=query_parameters)
        data = response.data
        bookmarks = data['results']

        self.assertEqual(len(bookmarks), 2)
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['num_pages'], 1)

        # As bookmarks are sorted by -created so we will compare in that order.
        self.assert_valid_bookmark_response(bookmarks[0], self.bookmark_2, optional_fields=True)
        self.assert_valid_bookmark_response(bookmarks[1], self.bookmark_1, optional_fields=True)

    def test_get_bookmarks_with_pagination(self):
        """
        Test that requesting bookmarks for a course return results with pagination 200 code.
        """
        query_parameters = 'course_id={}&page_size=1'.format(self.course_id)
        response = self.send_get(client=self.client, url=reverse('bookmarks'), query_parameters=query_parameters)

        bookmarks = response.data['results']

        # Pagination assertions.
        self.assertEqual(response.data['count'], 2)
        self.assertIn('page=2&page_size=1', response.data['next'])
        self.assertEqual(response.data['num_pages'], 2)

        self.assertEqual(len(bookmarks), 1)
        self.assert_valid_bookmark_response(bookmarks[0], self.bookmark_2)

    def test_get_bookmarks_with_invalid_data(self):
        """
        Test that requesting bookmarks with invalid data returns a 0 records.
        Scenarios:
            1) Invalid course id.
            2) Without course id.
        """
        # Invalid course id.
        response = self.send_get(client=self.client, url=reverse('bookmarks'), query_parameters='course_id=invalid')
        bookmarks = response.data['results']
        self.assertEqual(len(bookmarks), 0)

        # Without course id.
        response = self.send_get(client=self.client, url=reverse('bookmarks'))
        bookmarks = response.data['results']
        self.assertEqual(len(bookmarks), 0)

    def test_anonymous_access(self):
        """
        Test that an anonymous client (not logged in) cannot call GET or POST.
        """
        query_parameters = 'course_id={}'.format(self.course_id)
        self.send_get(
            client=self.anonymous_client,
            url=reverse('bookmarks'),
            query_parameters=query_parameters,
            expected_status=401
        )
        self.send_post(
            client=self.anonymous_client,
            url=reverse('bookmarks'),
            json_data={"usage_id": "test"},
            expected_status=401
        )

    def test_post_bookmark_successfully(self):
        """
        Test that posting a bookmark successfully returns newly created data with 201 code.
        """
        response = self.send_post(
            client=self.client,
            url=reverse('bookmarks'),
            json_data={'usage_id': unicode(self.video_3.location)}
        )

        # Assert Newly created bookmark.
        self.assertEqual(response.data['id'], "%s,%s" % (self.user.username, unicode(self.video_3.location)))
        self.assertEqual(response.data['course_id'], self.course_id)
        self.assertEqual(response.data['usage_id'], unicode(self.video_3.location))
        self.assertIsNotNone(response.data['created'])

    def test_post_bookmark_with_invalid_data(self):
        """
        Test that posting a bookmark for a block with invalid usage id returns a 400.
        Scenarios:
            1) Invalid usage id.
            2) Without usage id.
            3) With empty request.DATA
        """
        # Send usage_id with invalid format.
        response = self.send_post(
            client=self.client,
            url=reverse('bookmarks'),
            json_data={'usage_id': 'invalid'},
            expected_status=400
        )
        self.assertEqual(response.data['user_message'], "Invalid usage id")
        self.assertEqual(response.data['developer_message'], "Invalid usage id")

        # Send data without usage_id.
        response = self.send_post(
            client=self.client,
            url=reverse('bookmarks'),
            json_data={'course_id': 'invalid'},
            expected_status=400
        )
        self.assertEqual(response.data['user_message'], "No usage id provided")
        self.assertEqual(response.data['developer_message'], "No usage id provided")

        # Send empty data dictionary.
        response = self.send_post(
            client=self.client,
            url=reverse('bookmarks'),
            json_data={},
            expected_status=400
        )
        self.assertEqual(response.data['user_message'], "No data provided")
        self.assertEqual(response.data['developer_message'], "No data provided")

    def test_post_bookmark_for_non_existing_block(self):
        """
        Test that posting a bookmark for a block that does not exist returns a 400.
        """
        response = self.send_post(
            client=self.client,
            url=reverse('bookmarks'),
            json_data={'usage_id': 'i4x://arbi/100/html/340ef1771a094090ad260ec940d04a21'},
            expected_status=400
        )
        self.assertEqual(response.data['user_message'], "Invalid usage id")
        self.assertEqual(response.data['developer_message'], "Item with usage id not found")

    def test_unsupported_methods(self):
        """
        Test that DELETE, and PUT are not supported.
        """
        self.client.login(username=self.user.username, password=self.test_password)
        self.assertEqual(405, self.client.put(reverse('bookmarks')).status_code)
        self.assertEqual(405, self.client.delete(reverse('bookmarks')).status_code)


class BookmarksDetailViewTests(BookmarksViewTestsMixin):
    """
    This contains the tests for GET & DELETE methods of bookmark.views.BookmarksDetailView class
    """

    def test_get_bookmark_successfully(self):
        """
        The view should return a list of all courses.
        """
        response = self.send_get(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': unicode(self.video_1.location)}
            )
        )
        data = response.data
        self.assertIsNotNone(data)
        self.assert_valid_bookmark_response(data, self.bookmark_1)

    def test_get_bookmark_with_optional_fields(self):
        """
        The view should return a list of all courses.
        """
        query_parameters = 'course_id={}&fields=path,display_name'.format(self.course_id)

        response = self.send_get(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': unicode(self.video_1.location)}
            ),
            query_parameters=query_parameters
        )
        data = response.data
        self.assertIsNotNone(data)
        self.assert_valid_bookmark_response(data, self.bookmark_1, optional_fields=True)

    def test_get_bookmark_that_belongs_to_other_user(self):
        """
        """

        self.send_get(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': 'other', 'usage_id': unicode(self.video_1.location)}
            ),
            expected_status=404
        )

    def test_get_bookmark_that_does_not_exist(self):
        """
        """
        response = self.send_get(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': 'i4x://arbi/100/html/340ef1771a0940'}
            ),
            expected_status=404
        )
        self.assertEqual(response.data['user_message'], "The bookmark does not exist.")
        self.assertEqual(response.data['developer_message'], "Bookmark matching query does not exist.")

    def test_get_bookmark_with_invalid_usage_id(self):
        """
        """
        response = self.send_get(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': 'i4x'}
            ),
            expected_status=400
        )
        self.assertEqual(response.data['user_message'], "Invalid usage id")

    def test_anonymous_access(self):
        """
        Test that an anonymous client (not logged in) cannot call GET or DELETE.
        """
        url = reverse('bookmarks_detail', kwargs={'username': self.user.username, 'usage_id': 'i4x'})
        self.send_get(
            client=self.anonymous_client,
            url=url,
            expected_status=401
        )
        self.send_delete(
            client=self.anonymous_client,
            url=url,
            expected_status=401
        )

    def test_delete_bookmark_successfully(self):
        """
        The view should return a list of all courses.
        """
        query_parameters = 'course_id={}'.format(self.course_id)
        response = self.send_get(client=self.client, url=reverse('bookmarks'), query_parameters=query_parameters)
        data = response.data
        bookmarks = data['results']
        self.assertEqual(len(bookmarks), 2)

        self.send_delete(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': unicode(self.video_1.location)}
            )
        )

        response = self.send_get(client=self.client, url=reverse('bookmarks'), query_parameters=query_parameters)
        bookmarks = response.data['results']

        self.assertEqual(len(bookmarks), 1)

    def test_delete_bookmark_that_belongs_to_other_user(self):
        """
        """
        self.send_delete(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': 'other', 'usage_id': unicode(self.video_1.location)}
            ),
            expected_status=404
        )

    def test_delete_bookmark_that_does_not_exist(self):
        """
        """
        response = self.send_delete(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': 'i4x://arbi/100/html/340ef1771a0940'}
            ),
            expected_status=404
        )
        self.assertEqual(response.data['user_message'], "The bookmark does not exist.")
        self.assertEqual(response.data['developer_message'], "Bookmark matching query does not exist.")

    def test_delete_bookmark_with_invalid_usage_id(self):
        """
        """
        response = self.send_delete(
            client=self.client,
            url=reverse(
                'bookmarks_detail',
                kwargs={'username': self.user.username, 'usage_id': 'i4x'}
            ),
            expected_status=400
        )
        self.assertEqual(response.data['user_message'], "Invalid usage id")
