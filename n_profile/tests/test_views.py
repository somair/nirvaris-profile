import re, pdb

from datetime import date, timedelta

from django.contrib.auth.models import User, AnonymousUser, Group
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase, Client

from .commons import create_user_jack, create_user_james, create_user_group
from ..crypto import decrypt, user_activation_token, user_invitation_token
from ..forms import RegisterForm, LoginForm, ResendActivationEmailForm, ForgotPasswordForm, ChangeUserPasswordForm, UserDetailsForm
from ..views import RegisterView, UsersListView, UserDetailsView, InvitationView, ResendActivationEmailView, ForgotPasswordView, LoginView, ChangeUserPasswordView, UserProfileView, NV_AFTER_LOGIN_URL, NV_MAX_TOKEN_DAYS

class ProfileViewsTestCase(TestCase):

    def setUp(self):
        self.c = Client(HTTP_USER_AGENT='Mozilla/5.0')

    def tearDown(self):
        ...
    def test_logout(self):

        jack_user = create_user_jack(True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username,password='pass'),'Must login with the old credentials')

        response = c.get(reverse('logout'))

        self.assertEquals(response.status_code, 302,'Logout page should redirect to login')

        self.assertIn(response['location'], reverse('login'))

        response = c.get(reverse('login'))

        self.assertTrue(isinstance(response.context['user'], AnonymousUser))

    def test_user_details(self):

        c = self.c
        response = c.get(reverse('user-details',kwargs={'user_id':1}))

        self.assertEquals(response.status_code,403,'Not logged user shoould NOT get the page')

        jack_user = create_user_jack(True, True)

        self.assertTrue(c.login(username=jack_user.username, password='pass'),'Must login old credentials')

        response = c.get(reverse('user-details',kwargs={'user_id':jack_user.id}))

        self.assertEquals(response.status_code,200,'Should return 200')

        self.assertEqual(response.resolver_match.func.__name__, UserDetailsView.as_view().__name__)

        self.assertTemplateUsed(response, 'user-details.html')

    def test_users_list(self):

        c = self.c
        response = c.get(reverse('users-list'))

        self.assertEquals(response.status_code,403,'Not logged user shoould NOT get the page')

        jack_user = create_user_jack(True, True)

        self.assertTrue(c.login(username=jack_user.username, password='pass'),'Must login old credentials')

        response = c.get(reverse('users-list'))

        self.assertEquals(response.status_code,200,'Should be 200')

        self.assertEqual(response.resolver_match.func.__name__, UsersListView.as_view().__name__)

        self.assertTemplateUsed(response, 'users-list.html')

    def test_change_user_details(self):

        jack_user = create_user_jack(True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username, password='pass'),'Must login with the old credentials')

        response = c.post(reverse('user-profile'), {
            'name':'Jacky Changed Awesome Daniels',
            'username': 'jack_changed',
            'email':'jack_changed@awesome.com',
            'current_password': 'pass',
            'action':'form_details',

        })

        self.assertTrue(User.objects.filter(username='jack_changed').exists(),'User was not registered')

        cahnged_user = User.objects.get(username='jack_changed')

        self.assertEquals(cahnged_user.first_name,'Jacky','user First name does not match')
        self.assertEquals(cahnged_user.last_name,'Changed Awesome Daniels','user Last name does not match')
        self.assertEquals(cahnged_user.email,'jack_changed@awesome.com','user Email does not match')
        self.assertEquals(cahnged_user.username,'jack_changed','user username does not match')

        self.assertTrue(c.login(username='jack_changed',password='pass'),'Must login with the new username')

        response = c.post(reverse('user-profile'), {
            'name':'Jacky Changed Awesome Daniels',
            'username': 'jack_changed2',
            'email':'jackdetailspost@awesome.com',
            'password': 'password2',
            'action':'form_details',
        })

        self.assertEquals(response.status_code,200,'Should stay on the page as current password is wrong')

        self.assertTrue(c.login(username='jack_changed',password='pass'),'Should login with the old credentials as did not change the username')

        response = c.post(reverse('user-profile'), {
            'name':'',
            'username': '',
            'email':'',
            'password': '',
            'action':'form_details',

        })

        self.assertEquals(response.status_code,200,'Should stay on the page as fields are blank')


        self.assertTrue(c.login(username='jack_changed',password='pass'),'Should login with the old credentials as did not change the username')


    def NONEtest_change_user_photo(self):

        jack_user = create_user_jack(True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username, password='pass'),'Must login with the old credentials')

        user = User.objects.get(username='jack')

        self.assertEquals(user.first_name,'Jack','user Full Name does not match')
        self.assertEquals(user.last_name,'Awesome Daniels','user Full Name does not match')
        self.assertEquals(user.email,'jack@awesome.com','user Email does not match')

        response = c.get(reverse('user-profile'))

        content = str(response.content)

        self.assertTrue(re.search(re.compile('<div class="profile-usertitle-name">' + jack_user.get_full_name() + '</div>'), content),'div Full Name does not have the correct value')
        self.assertTrue(re.search(re.compile('<div class="profile-usertitle-email">' + jack_user.email + '</div>'), content),'div Email does not have the correct value')


        with open('user-photo.jpg', 'rb') as data:
            response = c.post('user-profile', {
                'action': 'form_photo',
                'image_file': data
            })

            self.assertEquals(response.status_code,200,'Fileuplaod ok')


    def test_change_password(self):

        jack_user = create_user_jack(True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username,password='pass'),'Must login with the old credentials')

        response = c.post(reverse('change-password'), {
            'current_password':'pass',
            'new_password': 'password2',
            'confirm_new_password':'password2',
        })

        self.assertEquals(response.status_code,302,'Should redirect to logout')

        self.assertTrue(response['Location'] in reverse('logout'),'Should redirect to logout')

        self.assertTrue(c.login(username=jack_user.username,password='password2'),'Must login with the new credentials')

        response = c.post(reverse('change-password'), {
            'current_password':'password',
            'new_password': 'password3',
            'confirm_new_password':'password3',

        })

        self.assertEquals(response.status_code,200,'Should stay on the page as current password is wrong')

        self.assertTrue(c.login(username=jack_user.username,password='password2'),
        'Should login with the old credentials as did not change the password')

        response = c.post(reverse('change-password'), {
            'current_password':'password2',
            'new_password': 'password4',
            'confirm_new_password':'password3',

        })

        self.assertEquals(response.status_code,200,'Should stay on the page as new password does not match')

        self.assertTrue(c.login(username=jack_user.username,password='password2'),
        'Should login with the old credentials as did not change the password')

        response = c.post(reverse('change-password'), {
            'current_password':'',
            'new_password': '',
            'confirm_new_password':'',

        })

        self.assertEquals(response.status_code,200,'Should stay on the page as form is blank')

        self.assertTrue(c.login(username=jack_user.username,password='password2'),
        'Should login with the old credentials as did not change the password')

    def test_get_change_user_details_view(self):

        jack_user = create_user_jack(True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username,password='pass'),'Must login with the old credentials')

        response = c.get(reverse('user-profile'))

        self.assertEquals(response.status_code,200,'Logged user shoould get the page')

        self.assertEqual(response.resolver_match.func.__name__, UserProfileView.as_view().__name__)

        self.assertTemplateUsed(response, 'user-profile.html')

        self.assertTrue(isinstance(response.context['form_details'], UserDetailsForm))

        content = str(response.content)

        self.assertTrue(re.search(re.compile('<input.+?name="current_password"'), content),'No input form field password')
        self.assertTrue(re.search(re.compile('<input.+?name="name"'), content),'No input form field name')
        self.assertTrue(re.search(re.compile('<input.+?name="username"'), content),'No input form field username')
        self.assertTrue(re.search(re.compile('<input.+?name="email"'), content),'No input form field email')

        self.assertTrue(re.search(re.compile('<input.+?name="name".+?value=.+?' + jack_user.get_full_name() + '.+?/>'), content),'input name does not have the correct value')
        self.assertTrue(re.search(re.compile('<input.+?name="username".+?value=.+?' + jack_user.username + '.+?/>'), content),'input username does not have the correct value')
        self.assertTrue(re.search(re.compile('<input.+?name="email".+?value=.+?' + jack_user.email + '.+?/>'), content),'input email does not have the correct value')

    def test_get_change_password_view(self):

        jack_user = create_user_jack(True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username,password='pass'),'Must login with the old credentials')

        response = c.get(reverse('change-password'))

        self.assertEquals(response.status_code,200,'Logged user shoould get the page')

        self.assertEqual(response.resolver_match.func.__name__, ChangeUserPasswordView.as_view().__name__)

        self.assertTemplateUsed(response, 'change-password.html')

        content = str(response.content)

        self.assertTrue(isinstance(response.context['form'], ChangeUserPasswordForm))

        self.assertTrue(re.search(re.compile('<input.+?name="current_password"'), content),
        'No input form field current_password')

        self.assertTrue(re.search(re.compile('<input.+?name="new_password"'), content),
        'No input form field new_password')

        self.assertTrue(re.search(re.compile('<input.+?name="confirm_new_password"'), content),
        'No input form field confirm_new_password')

    def test_invitation_token(self):

        g = create_user_group('Sales')
        invitation_token = user_invitation_token('new-jack@awesome.com', date.today(),[g.id])

        url_to_activate = reverse('invitation',kwargs={'token': str(invitation_token)})
        c = self.c
        response = c.get(url_to_activate)

        self.assertEquals(response.status_code,200)

        self.assertEqual(response.resolver_match.func.__name__, InvitationView.as_view().__name__)

        self.assertTemplateUsed(response, 'invitation.html')

        self.assertTrue(isinstance(response.context['form'],RegisterForm))

        self.assertTrue(response.context['form']['email'],'new-jack@awesome.com')

    def test_send_invite_user_email(self):


        mail.outbox = []
        c = self.c

        mail.outbox = []


        jack_user = create_user_jack(True, True)

        c = self.c

        self.assertTrue(c.login(username=jack_user.username,password='pass'),'Must login with the old credentials')

        response = c.post(reverse('invite-user'),{
            'email':jack_user.email
        })

        self.assertEqual(len(mail.outbox), 0,'It should not have sent any email')

        response = c.post(reverse('invite-user'),{
            'email':''
        })

        self.assertEqual(len(mail.outbox), 0,'It should not have sent any email')

        mail.outbox = []
        g =create_user_group('Sales')
        response = c.post(reverse('invite-user'),{
            'email':'new-jack@awesome.com',
            'groups':g.id,
        })
        self.assertEqual(len(mail.outbox), 1,'No invitation email sent')

        message = mail.outbox[0]
        content = str(message.body)

        m = re.search(re.compile('<a.+?href=".+?/invitation/(.+?)"'), content)
        self.assertTrue(m,'No matching invitation link on email body')

        # check the activation link
        invitation_token = m.groups(1)[0]
        msg = decrypt(invitation_token).split(',')

        d = msg[3].split('-')
        dt = date(int(d[0]), int(d[1]), int(d[2]))

        self.assertEqual(msg[0], 'invite')
        self.assertEqual(msg[1], 'new-jack@awesome.com')

    def test_send_activation_email(self):

        mail.outbox = []
        c = self.c

        response = c.post(reverse('resend-activation-email'),{
            'email':'not-jack@awesome.com'
        })

        self.assertEquals(response.status_code, 200,'Invalid email should do nothing')

        self.assertEqual(len(mail.outbox), 0,'It should not have sent any email')

        response = c.post(reverse('resend-activation-email'),{
            'email':''
        })

        self.assertEquals(response.status_code, 200,'Invalid email should do nothing')

        self.assertEqual(len(mail.outbox), 0,'It should not have sent any email')

        mail.outbox = []

        jack_user = create_user_jack()

        response = c.post(reverse('resend-activation-email'),{
            'email':jack_user.email
        })
        self.assertEqual(len(mail.outbox), 1,'No activation email sent')

        message = mail.outbox[0]
        content = str(message.body)

        m = re.search(re.compile('<a.+?href=".+?/activation/(.+?)"'), content)
        self.assertTrue(m,'No matching activation link on email body')

        # check the activation link
        activation_token = m.groups(1)[0]
        msg = decrypt(activation_token).split(',')

        d = msg[2].split('-')
        dt = date(int(d[0]), int(d[1]), int(d[2]))

        self.assertTrue(User.objects.filter(username=msg[0], email=msg[1]).exists())

    def test_activation_expired_token(self):

        jack_user = create_user_jack()

        due_date = date.today()-timedelta(days=int(NV_MAX_TOKEN_DAYS)+1)

        activation_token = user_activation_token(jack_user.username, jack_user.email, due_date)

        url_to_activate = reverse('activation',kwargs={'token': str(activation_token)})
        c = self.c
        response = c.get(url_to_activate)

        self.assertEquals(response.status_code,200)

        self.assertFalse(User.objects.get(username=jack_user.username).is_active)

    def test_activation_token(self):

        jack_user = create_user_jack()

        activation_token = user_activation_token(jack_user.username, jack_user.email, date.today())

        url_to_activate = reverse('activation',kwargs={'token': str(activation_token)})
        c = self.c
        response = c.get(url_to_activate)

        self.assertEquals(response.status_code,200)

        self.assertTrue(User.objects.get(username=jack_user.username).is_active)

    def test_forgot_password_non_exist(self):

        mail.outbox = []
        c = self.c

        response = c.post(reverse('forgot-password'),{
            'email':'jacknonexist@awesome.com'
        })

        self.assertEquals(response.status_code, 200,'Invalid email should do nothing')

        self.assertEqual(len(mail.outbox), 0,'It should not have sent any email')

        response = c.post(reverse('forgot-password'),{
            'email':''
        })

        self.assertEquals(response.status_code, 200,'Invalid email should do nothing')

        self.assertEqual(len(mail.outbox), 0,'It should not have sent any email')

    def test_forgot_password(self):

        mail.outbox = []

        jack_user = create_user_jack()

        c = self.c

        response = c.post(reverse('forgot-password'),{
            'email':jack_user.email
        })

        self.assertEquals(response.status_code, 200,'Should redirect back')

        self.assertEqual(len(mail.outbox), 0,'No forgot password email sent')

        jack_user.is_active = True
        jack_user.save()

        response = c.post(reverse('forgot-password'),{
            'email':jack_user.email
        })

        self.assertEquals(response.status_code, 302,'Should redirect back')

        self.assertTrue(response['Location'] in reverse('forgot-password'))

        self.assertEqual(len(mail.outbox), 1,'No forgot password email sent')

        message = mail.outbox[0]
        content = str(message.body)

        m = re.search(re.compile('<span.+?id="new_password">(.+?)</span>'), content)
        self.assertTrue(m,'No matching password on email body')

        new_password = m.groups(1)[0]

        self.assertTrue(c.login(username=jack_user.username,password=new_password),'User should be able to login with the new password')


    def test_register_duplicated_email(self):

        c = self.c

        jack_user = create_user_jack(True)


        response = c.post(reverse('register'), {
            'name':'Jimmy Page',
            'username': 'jimmy',
            'email': jack_user.email,
            'password': 'password',
            'confirm_password':'password'
        })

        self.assertEquals(response.status_code,200)
        self.assertTrue(User.objects.filter(email=jack_user.email).count()==1,'User jimmy should NOT be registered')

    def test_register_empty_fields(self):

        c = self.c
        response = c.post(reverse('register'), {
            'name':'',
            'username': '',
            'email':'',
            'password': '',
            'confirm_password':''
        })
        self.assertEquals(response.status_code,200)

        self.assertFalse(User.objects.filter(username='').exists(),'User should NOT be registered')

    def test_register_no_matching_password(self):

        c = self.c

        response = c.post(reverse('register'), {
            'name':'John Lennon',
            'username': 'john',
            'email': 'johnlennon@some.com',
            'password': 'password',
            'confirm_password':'nomacthpassword'
        })

        self.assertEquals(response.status_code,200)

        self.assertFalse(User.objects.filter(username='john').exists(),'User should NOT be registered')

    def test_register_user(self):

        mail.outbox = []

        c = self.c

        # check the register
        response = c.post(reverse('register'), {
            'name':'Jack Awesome Daniels',
            'username': 'jack',
            'email':'jack@awesome.com',
            'password': 'password',
            'confirm_password':'password'
        })

        self.assertEquals(response.status_code,302,'Page not redirected')

        self.assertTrue(response['Location'] in reverse('resend-activation-email'))

        self.assertTrue(User.objects.filter(username='jack').exists(),'User was not registered')

        new_user = User.objects.get(username='jack')

        self.assertEquals(new_user.first_name,'Jack','user First name does not match')
        self.assertEquals(new_user.last_name,'Awesome Daniels','user Last name does not match')
        self.assertEquals(new_user.email,'jack@awesome.com','user Email does not match')
        self.assertEquals(new_user.username,'jack','user username does not match')

        self.assertFalse(User.objects.get(username='jack').is_active)

        # check the activation email
        self.assertEqual(len(mail.outbox), 1,'No activation email sent')

        message = mail.outbox[0]
        content = str(message.body)

        m = re.search(re.compile('<a.+?href=".+?/activation/(.+?)"'), content)
        self.assertTrue(m,'No matching activation link on email body')

        # check the activation link
        activation_token = m.groups(1)[0]
        url_to_activate = reverse('activation',kwargs={'token': str(activation_token)})
        response = c.get(url_to_activate)

        self.assertEquals(response.status_code,200)

        self.assertTrue(User.objects.get(username='jack').is_active)

    def test_login_non_active_user(self):

        jack_user = create_user_jack(False)

        c = self.c

        # check login with username not active user
        response = c.post(reverse('login'), {
            'email_or_username':jack_user.username,
            'password': 'pass',
        })
        self.assertEquals(response.status_code, 200,'Login page should not login and redirect')

        context_user = response.context['user']

        self.assertFalse(context_user.is_authenticated(),'Conext user should not be authenticated')

        # check login with email not active user
        response = c.post(reverse('login'), {
            'email_or_username':jack_user.email,
            'password': 'pass',
        })

        self.assertEquals(response.status_code, 200,'Login page should not login and redirect')

        context_user = response.context['user']

        self.assertFalse(context_user.is_authenticated(),'Conext user should not be authenticated')

    def test_login_active_user(self):

        jack_user = create_user_jack(True)


        c = self.c
        # check login with username
        response = c.post(reverse('login'), data={
            'email_or_username':jack_user.username,
            'password': 'pass',
        })

        self.assertEquals(response.status_code, 302,'Login page should redirect to AFTER_LOGIN_URL')
        self.assertIn(NV_AFTER_LOGIN_URL,response['Location'])


        # check login with email
        response = c.post(reverse('login'), data={
            'email_or_username':jack_user.email,
            'password': 'pass',
        })

        self.assertEquals(response.status_code, 302,'Login page should redirect to AFTER_LOGIN_URL')

        self.assertIn(NV_AFTER_LOGIN_URL,response['Location'])


    def test_get_resend_activation_view(self):

        c = self.c

        response = c.get(reverse('resend-activation-email'))

        self.assertEquals(response.status_code,200)

        self.assertEqual(response.resolver_match.func.__name__, ResendActivationEmailView.as_view().__name__)

        self.assertTemplateUsed(response, 'resend-activation-email.html')

        self.assertTrue(isinstance(response.context['form'], ResendActivationEmailForm))

        content = str(response.content)
        self.assertTrue(re.search(re.compile('<input.+?name="email"'), content),'No input form field email')



    def test_get_forgot_password_view(self):

        c = self.c

        response = c.get(reverse('forgot-password'))

        self.assertEquals(response.status_code,200)

        self.assertEqual(response.resolver_match.func.__name__, ForgotPasswordView.as_view().__name__)

        self.assertTemplateUsed(response, 'forgot-password.html')


        content = str(response.content)

        self.assertTrue(isinstance(response.context['form'], ForgotPasswordForm))


        self.assertTrue(re.search(re.compile('<input.+?name="email"'), content),'No input form field email')

    def test_get_register_view(self):

        c = self.c

        response = c.get(reverse('register'))

        self.assertEquals(response.status_code,200)

        self.assertEqual(response.resolver_match.func.__name__, RegisterView.as_view().__name__)

        self.assertTemplateUsed(response, 'register.html')

        self.assertTrue(isinstance(response.context['form'],RegisterForm))

        content = str(response.content)
        self.assertTrue(re.search(re.compile('<input.+?name="name"'), content),'No input form field name')
        self.assertTrue(re.search(re.compile('<input.+?name="username"'), content),'No input form field username')
        self.assertTrue(re.search(re.compile('<input.+?name="email"'), content),'No input form field email')
        self.assertTrue(re.search(re.compile('<input.+?name="password"'), content),'No input form field password')
        self.assertTrue(re.search(re.compile('<input.+?name="confirm_password"'), content),'No input form field confirm_password')



    def test_get_login_view(self):

        c = self.c

        response = c.get(reverse('login'))

        self.assertEquals(response.status_code,200)

        self.assertEqual(response.resolver_match.func.__name__, LoginView.as_view().__name__)

        self.assertTemplateUsed(response, 'login.html')

        content = str(response.content)

        self.assertTrue(isinstance(response.context['form'], LoginForm))

        self.assertTrue(re.search(re.compile('<input.+?name="email_or_username"'), content),'No input form field email_or_username')
        self.assertTrue(re.search(re.compile('<input.+?name="password"'), content),'No input form field password')
