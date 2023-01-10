from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Page
from django.test import Client, TestCase
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='Ivan')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.urls = {
            'index': [
                'posts:index',
                None,
                'posts/index.html'],
            'group_posts': [
                'posts:group_posts',
                {'slug': cls.group.slug},
                'posts/group_list.html'],
            'profile': [
                'posts:profile',
                {'username': cls.post.author},
                'posts/profile.html'],
            'post_detail': [
                'posts:post_detail',
                {'post_id': cls.post.id},
                'posts/post_detail.html'],
            'post_edit': [
                'posts:post_edit',
                {'post_id': cls.post.id},
                'posts/create_post.html'],
            'post_create': [
                'posts:post_create',
                None,
                'posts/create_post.html']
        }
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text="Тестовый комментарий",
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)

    def common_tests_for_fields_of_some_pages(self, response_context, is_page):
        if is_page:
            self.assertIsInstance(response_context.get('page_obj'), Page)
            post = response_context.get('page_obj')[0]
        else:
            post = response_context.get('post')
        self.assertIsInstance(post, Post)
        post_text_0 = post.text
        post_group_0 = post.group
        post_author_0 = post.author
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_group_0, self.post.group)
        self.assertEqual(post_author_0, self.post.author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for page_name, kwargs, template in self.urls.values():
            with self.subTest(page_name):
                response = self.authorized_client.get(reverse(page_name,
                                                              kwargs=kwargs))
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        self.common_tests_for_fields_of_some_pages(response.context, True)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        self.common_tests_for_fields_of_some_pages(response.context, True)
        self.assertEqual(response.context.get('group'), self.group)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': self.post.author})
        )
        self.common_tests_for_fields_of_some_pages(response.context, True)
        self.assertEqual(response.context.get('author'), self.post.author)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.common_tests_for_fields_of_some_pages(response.context, False)
        self.assertEqual(response.context.get('author'), self.post.author)
        self.assertEqual(response.context.get('post'), self.post)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form = response.context.get('form')
                form_field = response.context.get('form').fields[value]
                self.assertIsInstance(form, PostForm)
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form = response.context.get('form')
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form, PostForm)
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        self.post = Post.objects.create(
            text='Тестовый текст проверка как добавился',
            author=self.user,
            group=self.group)
        response_index = self.authorized_client.get(
            reverse('posts:index'))
        response_group = self.authorized_client.get(
            reverse('posts:group_posts',
                    kwargs={'slug': f'{self.group.slug}'}))
        response_profile = self.authorized_client.get(
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}))
        index = response_index.context.get('page_obj')
        group = response_group.context.get('page_obj')
        profile = response_profile.context.get('page_obj')
        self.assertIn(self.post, index, 'поста нет на главной')
        self.assertIn(self.post, group, 'поста нет в профиле')
        self.assertIn(self.post, profile, 'поста нет в группе')

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем, чтобы созданный Пост с группой
           не попап в чужую группу."""
        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        posts_count = Post.objects.filter(group=self.group).count()
        self.post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user,
            group=group2)
        self.group = Post.objects.filter(group=self.group).count()
        self.assertEqual(self.group, posts_count, 'поста нет в другой группе')

    def test_comment_correct_context(self):
        """Авторизованный пользователь может создать комментарий и он появится
           на странице поста."""
        comments_count = Comment.objects.count()
        form_data_1 = {'text': 'Тестовый коммент'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data_1,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(Comment.objects.filter(text='Тестовый коммент').
                        exists())

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.guest_client.get(reverse('posts:index'))
        Post.objects.get(id=1).delete()
        response_2 = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_2.content)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(title='Тестовая группа',
                                         slug='test_group',
                                         description='Тестовое описание')
        posts: list = []
        for i in range(settings.NUMBER_OF_POSTS_PER_PAGE + 3):
            posts.append(Post(text=f'Тестовый текст {i}',
                              group=cls.group,
                              author=cls.user))
        Post.objects.bulk_create(posts)

    def setUp(self):
        self.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context.get('page_obj')),
                         settings.NUMBER_OF_POSTS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        response = self.guest_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context.get('page_obj')), 3)
