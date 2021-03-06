from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import simplejson
from django.views.generic.list_detail import object_list, object_detail

from ideas.models import Idea, IdeasUsers
from ideas.forms import IdeaForm

def index(request):
    return object_list(request, queryset=Idea.objects.all())

def detail(request, idea_pk):
    idea = get_object_or_404(Idea, id=idea_pk)
    can_edit = request.user.is_staff or request.user == idea.submitted_by
    points = request.user.get_profile().available_points
    return render_to_response("ideas/detail.html",
                              {"can_edit": can_edit,
                               "points":points,
                               "idea":idea},
                              context_instance=RequestContext(request))

@login_required
def new(request):
    # @@@ Maybe should auto-vote your own things?
    initial = {'submitted_by':request.user.id}
    form = IdeaForm(request.POST or None, initial=initial)
    if request.method == "POST":
        if form.is_valid():
            if form.save():
                return HttpResponseRedirect(reverse("idea-index"))
    return render_to_response("ideas/new.html", {"form":form},
                              context_instance=RequestContext(request))

@login_required
def edit(request, idea_pk):
    idea = get_object_or_404(Idea, id=idea_pk, submitted_by=request.user)
    form = IdeaForm(request.POST or None, instance=idea)
    if request.method == "POST":
        if form.is_valid():
            if form.save():
                return HttpResponseRedirect(reverse("idea-index"))
    return render_to_response("ideas/new.html", {"form":form},
                              context_instance=RequestContext(request))

@login_required
def vote(request, idea_pk, amount=0):
    # @@@ Maybe shouldn"t be able to unvote on your own things.
    amount = int(amount)
    user_profile = request.user.get_profile()
    idea = get_object_or_404(Idea, id=idea_pk)
    
    if user_profile.available_points < amount:
        if request.is_ajax():
            return HttpResponse(
                simplejson.dumps({"error":"Not enough points"})
            )
        else:
            messages.error(request, "Not enough points.")
            return HttpResponseRedirect(reverse("idea-detail", kwargs={"idea_pk": idea.id}))

    try:
        user_vote = IdeasUsers.objects.get(idea=idea, user=request.user)
    except IdeasUsers.DoesNotExist:
        user_vote = IdeasUsers(idea=idea, user=request.user)
    user_vote.points = amount
    user_vote.save()
    user_profile.recalculate_points()
    if amount == 0:
        msg = "You have successfully unvoted."
    else:
        msg = "You have successfully voted %s points." % amount
    messages.success(request, msg)
    return HttpResponseRedirect(reverse("idea-detail", kwargs={"idea_pk": idea.id}))

def popular(request):
    ideas = Idea.objects.all().annotate(
        num_points=Sum('ideasusers__points')
    ).order_by('-num_points')
    return render_to_response('ideas/popular.html',
                              {'ideas':ideas},
                              context_instance=RequestContext(request))
