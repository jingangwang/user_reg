import datetime
from django.shortcuts import render, redirect

from user_reg import settings
from . import models, forms
import hashlib
# Create your views here.


def hash_code(s, salt='login'):
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())
    return h.hexdigest()


def index(request):
    return render(request, 'login/index.html')


def login(request):
    if request.session.get('is_login', None):
        return redirect("/index/")
    if request.method == 'POST':
        login_form = forms.UserForm(request.POST)
        message = "所有字段都必须填写！"
        if login_form.is_valid():
            username = login_form.cleaned_data.get("username")
            password = login_form.cleaned_data.get("password")
            try:
                user = models.User.objects.get(name=username)
                if not user.has_confirmed:
                    message = "该用户还未通过邮件确认！"
                    return render(request, 'login/login.html', locals())
                if user.password == hash_code(password):
                    request.session['is_login'] = True
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    return redirect('/index/')
                else:
                    message = "密码不正确！"
            except:
                message = "用户名不存在！"
        return render(request, 'login/login.html', locals())
    login_form = forms.UserForm()
    return render(request, 'login/login.html', locals())


def make_confirm_string(user):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code = hash_code(user.name, now)
    models.ConfirmString.objects.create(code=code, user=user)
    return code


def send_email(email, code):
    from django.core.mail import EmailMultiAlternatives
    subject = "来自注册网站的注册确认邮件"
    text_content = "如果你看到这条消息，说明你的邮箱服务器不支持html的链接功能，请联系系统管理员！"
    html_content = '''
    <p>感谢注册<a href ='http://{}/confirm/?code={}' target=blank>www.wangjingang.com</a></p>
    <p>请点击站点链接完成注册确认！</p>
    <p>此链接有效期为{}天！</p>
    '''.format('127.0.0.1:8000', code, settings.CONFIRM_DAYS)
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def register(request):
    if request.method == 'POST':
        register_form = forms.RegisterForm(request.POST)
        message = "所有字段都必须填写！"
        if register_form.is_valid():
            username = register_form.cleaned_data.get("username")
            password1 = register_form.cleaned_data.get("password1")
            password2 = register_form.cleaned_data.get("password2")
            email = register_form.cleaned_data.get("email")
            sex = register_form.cleaned_data.get("sex")
            if password1 != password2:
                message = "两次输入的密码不一致"
                return render(request, "login/register.html", locals())
            user_username = models.User.objects.filter(name=username)
            if user_username:
                message = "该用户名已注册"
                return render(request, "login/register.html", locals())
            user_email = models.User.objects.filter(email=email)
            if user_email:
                message = "该邮箱已注册"
                return render(request, "login/register.html", locals())
            new_user = models.User.objects.create()
            new_user.name = username
            new_user.password = hash_code(password1)
            new_user.email = email
            new_user.sex = sex
            new_user.save()
            
            code = make_confirm_string(new_user)
            send_email(email, code)
            return redirect("/login/")
    register_form = forms.RegisterForm()
    return render(request, 'login/register.html', locals())


def logout(request):
    if not request.session.get('is_login', None):
        return redirect("/index/")
    request.session.flush()
    return redirect('/index/')


def user_confirm(request):
    code = request.GET.get('code', None)
    message = ''
    try:
        confirm = models.ConfirmString.objects.get(code=code)
    except:
        message = "无效的确认请求！"
        return render(request, "login/confirm.html", locals())

    c_time = confirm.c_time
    now = datetime.datetime.now()
    if now > (c_time + datetime.timedelta(settings.CONFIRM_DAYS)).replace(tzinfo=None):
        confirm.user.delete()
        message = "您的邮件已经过期!请重新注册！"
        return render(request, "login/confirm.html", locals())
    else:
        confirm.user.has_confirmed = True
        confirm.user.save()
        confirm.delete()
        message = '感谢确认，请使用账户登录！'
        return render(request, "login/confirm.html", locals())