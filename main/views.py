from django.shortcuts import render, redirect
from django.core.mail import send_mail
from app.essay_rephraser import process_essay, prompt_generator
from app.load_resources import ResourceValues
from app.ai_detector import copyleaks_detector, gptzero_detector
from accounts.models import UserExtraFields
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect

from .models import Essays
from .stripe_handler import stripe_purchase_url, stripe_special_purchase_url, cancel_subscription
from .forms import RephraseForm, SetKeyForm
from django.contrib import messages
import stripe

# imoprt login view from django-allauth
from allauth.account.views import LoginView, SignupView, LogoutView

stripe.api_key=ResourceValues.stripe_key

def rephase_essay_view(request, id):
    essay = Essays.objects.get(id=id)
    ai_detection_result = {
        True: ResourceValues.ai_detection,
        False: ResourceValues.human_detection,
    }
    gptzero_res = ai_detection_result[gptzero_detector(essay.rephrased_essay)]
    copyleaks_res = ai_detection_result[copyleaks_detector(essay.rephrased_essay)]
    return render(request, "main/rephrase.html", {"essay": essay , 'gptzero_res': gptzero_res, 'copyleaks_res': copyleaks_res})

def cancel_sub(request, id):
    cancel_subscription(id)
    return redirect('profile')

def logout_redirect_view(request):
    return redirect('account_logout')

def profile_view(request):
    user=User.objects.get(username=request.user)
    user_fields=UserExtraFields.objects.get(user=request.user)

    if request.GET.get('id'):
        stripe_id = request.GET.get('id')
        session = stripe.checkout.Session.retrieve(stripe_id)
        metadata = session.get("metadata", {})
        if metadata:
            subscription_id=session.get('subscription')
            setattr(user_fields, 'subscribed', True)
            user_fields.save()
            setattr(user_fields, 'subscription_id', subscription_id)
            user_fields.save()
            # Set default API keys for subscribed users
            setattr(user_fields, 'prowritingaid_api_key', ResourceValues.openai_api_key_default_val)
            user_fields.save()
            setattr(user_fields, 'openai_api_key', ResourceValues.prowritingaid_api_key_default_val)
            user_fields.save()
        
    if not user.is_staff:
        stripe_url=stripe_purchase_url(user)
    else:
        stripe_url=stripe_special_purchase_url(user)

    # User rephrased essay info
    essays=Essays.objects.filter(user=user)
    if len(essays)==0:
        essays=None
    form = SetKeyForm()

    if request.method == "GET":
        return render(request, "main/profile.html", {"form":form, "user":user, "user_fields":user_fields, "stripe_url":stripe_url, "essays":essays})

    if request.method == "POST":
        # form = SetKeyForm(request.POST)
        # if form.is_valid():
            # data=form.cleaned_data
        data=request.POST
        if data['openai_api_key']:
            setattr(user_fields, 'openai_api_key', data['openai_api_key'])
            user_fields.save()
        if data['prowritingaid_api_key']:
            setattr(user_fields, 'prowritingaid_api_key', data['prowritingaid_api_key'])
            user_fields.save()
    return redirect('profile')
    # return render(request, "main/gpt.html", {"form": form, "user":user, "user_fields":user_fields, "stripe_url":stripe_url, "essays":essays})
    # return render(request, 'main/profile.html')
    
def contact_view(request):
    if request.user.is_authenticated:
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        send_mail(subject='New message',
            message=message,
            from_email=email,
            recipient_list=['eagle.smile.ace@gmail.com'])
        print(name, email, message)
        return render(request, "main/index.html")    
    if request.method == "POST":
        return redirect("accounts/login")
    return render(request, "main/index.html")

def service_view(request):
    if request.user.is_authenticated:
        reph_essay=None
        orig_essay=None
        openai_api_key=UserExtraFields.objects.get(user=request.user).openai_api_key
        prowritingaid_api_key=UserExtraFields.objects.get(user=request.user).prowritingaid_api_key
        essay=request.POST.get('textarea')
        approach=request.POST.get('approach')
        context=request.POST.get('context')
        if context==None:
            context=False
        else:
            context=True
        randomness_str=request.POST.get('randomness')
        if randomness_str==None:
            randomness=0
        else:
            randomness=int(randomness_str)
        tone=request.POST.get('tone')
        difficulty=request.POST.get('difficulty')
        additional_adjectives=request.POST.get('adj')
        model=request.POST.get('model')
        print(essay, approach, context, randomness, tone, difficulty, additional_adjectives, model)
        try:
            # data = form.cleaned_data
            rephrase_essay = process_essay(
                essay=essay,
                approach=approach,
                context=context,
                randomness=randomness,
                tone=tone,
                difficulty=difficulty,
                additional_adjectives=additional_adjectives,
                openaiapikey=openai_api_key,
                pwaidapikey=prowritingaid_api_key,
                username=request.user.username,
                model=model,
            )
            essay = Essays.objects.create(
                original_essay=essay,
                rephrased_essay=rephrase_essay,
                user=request.user,
            )
            print(rephrase_essay)
            essay.save()
            reph_essay=essay.rephrased_essay
            orig_essay=essay.original_essay
            # ai_detection_result = {
            #     True: ResourceValues.ai_detection,
            #     False: ResourceValues.human_detection,
            # }
            # gptzero_res = ai_detection_result[gptzero_detector(rephrase_essay)]
            # copyleaks_res = ai_detection_result[copyleaks_detector(rephrase_essay)]
            messages.success(request, "Essay rephrased successfully!")
            # return redirect("rephrase", id=essay.id)
        except Exception as e:
            reph_essay=None
            orig_essay=None
            messages.warning(request, "Error occured while rephrasing essay!")
        return render(request, "main/service.html", {"request":request, "result":reph_essay, "orig":orig_essay})
        
    if request.method == "POST":
        return redirect("accounts/login")
    return render(request, "main/service.html", {"request":request, "result":reph_essay, "orig":orig_essay})

def landing_view(request):

    if request.user.is_authenticated:
        reph_essay=""
        orig_essay=""
        openai_api_key=UserExtraFields.objects.get(user=request.user).openai_api_key
        prowritingaid_api_key=UserExtraFields.objects.get(user=request.user).prowritingaid_api_key
        essay=request.POST.get('textarea')
        approach=request.POST.get('approach')
        context=request.POST.get('context')
        if context==None:
            context=False
        else:
            context=True
        randomness_str=request.POST.get('randomness')
        if randomness_str==None:
            randomness=0
        else:
            randomness=int(randomness_str)
        tone=request.POST.get('tone')
        difficulty=request.POST.get('difficulty')
        additional_adjectives=request.POST.get('adj')
        model=request.POST.get('model')
        print(essay, approach, context, randomness, tone, difficulty, additional_adjectives, model)
        try:
            # data = form.cleaned_data
            rephrase_essay = process_essay(
                essay=essay,
                approach=approach,
                context=context,
                randomness=randomness,
                tone=tone,
                difficulty=difficulty,
                additional_adjectives=additional_adjectives,
                openaiapikey=openai_api_key,
                pwaidapikey=prowritingaid_api_key,
                username=request.user.username,
                model=model,
            )
            essay = Essays.objects.create(
                original_essay=essay,
                rephrased_essay=rephrase_essay,
                user=request.user,
            )
            print(rephrase_essay)
            if orig_essay!="":
                essay.save()
                reph_essay=essay.rephrased_essay
                orig_essay=essay.original_essay
                # ai_detection_result = {
                #     True: ResourceValues.ai_detection,
                #     False: ResourceValues.human_detection,
                # }
                # gptzero_res = ai_detection_result[gptzero_detector(rephrase_essay)]
                # copyleaks_res = ai_detection_result[copyleaks_detector(rephrase_essay)]
                messages.success(request, "Essay rephrased successfully!")
                # return redirect("rephrase", id=essay.id)
        except Exception as e:
            reph_essay=None
            orig_essay=None
            messages.warning(request, "Error occured while rephrasing essay!")
        return render(request, "main/service.html", {"request":request, "result":reph_essay, "orig":orig_essay})
        
    if request.method == "POST":
        return redirect("accounts/login")
    return render(request, "main/service.html", {"request":request, "result":reph_essay, "orig":orig_essay})

# Create your views here.
def home_view(request):

    # if not request.user.is_authenticated:
    #     return redirect("account_login")

    reph_essay=None
    orig_essay=None
    # openai_api_key=UserExtraFields.objects.get(user=request.user).openai_api_key
    # prowritingaid_api_key=UserExtraFields.objects.get(user=request.user).prowritingaid_api_key

    # if request.method == "GET":
    #     # return render(request, "main/home.html", {"request":request, "result":reph_essay, "orig":orig_essay, "openai_api_key":openai_api_key, "prowritingaid_api_key":prowritingaid_api_key})
    #     return render(request, "main/index.html")
    # essay=request.POST.get('textarea')
    # approach=request.POST.get('approach')
    # context=request.POST.get('context')
    # if context==None:
    #     context=False
    # else:
    #     context=True
    # randomness=int(request.POST.get('randomness'))
    # tone=request.POST.get('tone')
    # difficulty=request.POST.get('difficulty')
    # additional_adjectives=request.POST.get('adj')
    # model=request.POST.get('model')
    
    # # form = RephraseForm()
    # # if request.method == "POST":
    #     # form = RephraseForm(request.POST)
    #     # if form.is_valid():
    # try:
    #     # data = form.cleaned_data
    #     rephrase_essay = process_essay(
    #         essay=essay,
    #         approach=approach,
    #         context=context,
    #         randomness=randomness,
    #         tone=tone,
    #         difficulty=difficulty,
    #         additional_adjectives=additional_adjectives,
    #         openaiapikey=openai_api_key,
    #         pwaidapikey=prowritingaid_api_key,
    #         username=request.user.username,
    #         model=model,
    #     )
    #     essay = Essays.objects.create(
    #         original_essay=essay,
    #         rephrased_essay=rephrase_essay,
    #         user=request.user,
    #     )
    #     print(rephrase_essay)
    #     essay.save()
    #     reph_essay=essay.rephrased_essay
    #     orig_essay=essay.original_essay
    #     # ai_detection_result = {
    #     #     True: ResourceValues.ai_detection,
    #     #     False: ResourceValues.human_detection,
    #     # }
    #     # gptzero_res = ai_detection_result[gptzero_detector(rephrase_essay)]
    #     # copyleaks_res = ai_detection_result[copyleaks_detector(rephrase_essay)]
    #     messages.success(request, "Essay rephrased successfully!")
    #     # return redirect("rephrase", id=essay.id)
    # except Exception as e:
    #     reph_essay=None
    #     orig_essay=None
    #     messages.warning(request, "Error occured while rephrasing essay!")
    # return render(request, "main/home.html", {"request":request, "result":reph_essay, "orig":orig_essay, "openai_api_key":openai_api_key, "prowritingaid_api_key":prowritingaid_api_key})
    return render(request, "main/index.html")