from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
import hashlib, datetime, random
from user.forms import RegistrationForm
from user.models import UserProfile
from django.core.mail import send_mail


@login_required
def home(request):
    return render(request, 'home.html')

def signup(request):
    jsonRsp = {}
    
    if request.method == 'GET':
        form = RegistrationForm()
        return render(request, 'signup.html')
    else:

        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            

            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            salt = hashlib.sha1(str(random.random()).encode('utf-8')).hexdigest()[:5]            
            activation_key = hashlib.sha1((salt+email).encode('utf-8')).hexdigest()            
            key_expires = timezone.now() + datetime.timedelta(2)

            #Obtener el nombre de usuario
            user=User.objects.get(username=username)

            # Crear el perfil del usuario                                                                                                                                 
            new_profile = UserProfile(user=user, activation_key=activation_key, 
                key_expires=key_expires)
            new_profile.save()

            """TODO
            Fuente del tutorial - https://contraslash.github.io/blog_legacy/30-user-registration-and-email-confirmation-in-django/
            Pendiente:
                - Envio del mail
                - url para recibir la confirmacion de mail
            """

            # # Enviar un email de confirmación
            # email_subject = 'Account confirmation'
            # email_body = "Hola %s, Gracias por registrarte. Para activar tu cuenta da clíck en este link en menos de 48 horas: http://127.0.0.1:8000/accounts/confirm/%s" % (username, activation_key)

            # send_mail(email_subject, email_body, 'leonardo.bisaro@gmail.com',
            #     [email], fail_silently=False)
            
            jsonRsp['ok'] = 'Registro correcto'

        else: 
            #jsonRsp['error'] = dict(form.errors.items())
            msgError = ''
            for field in form:
                if field.errors:
                    msgError += "<div><b>"+field.label+"</b> "
                    for err in field.errors:
                        msgError += "<span>"+err+"</span> "
                    msgError += "</div>"
            msgError = msgError.replace("First name", "Nombre")
            msgError = msgError.replace("Last name", "Apellido")
            jsonRsp['error'] = msgError
        return JsonResponse(jsonRsp)
    

def signin(request):
    jsonRsp = {}
    if request.method == 'GET':
        return render(request, 'signin.html')
    else:
        user = authenticate(request,username=request.POST['login_username'], password=request.POST['login_password'])
        
        if user:
            if user.is_active:
                login(request, user)
                jsonRsp['login_ok'] = 'Redireccionando al home'
            else:
                jsonRsp['login_error'] = 'La cuenta de usuario se encuentra inactiva'
        else:
            jsonRsp['login_error'] = 'El usuario o contraseña es invalido'
        return JsonResponse(jsonRsp)


@login_required
def signout(request):
    logout(request)
    return redirect('signin')
