import datetime
from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import User, Listing, Comment, Bid, Watchlist

class NewListingForm(forms.Form):
    title = forms.CharField(label="", widget=forms.TextInput(attrs={'placeholder': 'Listing Title', 'class': 'form-control'}))
    category = forms.CharField(label="Category", max_length=2, widget=forms.Select(choices = Listing.CATEGORY_CHOICES, attrs={'class': 'form-control'}))
    description = forms.CharField(label="", widget=forms.Textarea(attrs={'placeholder': 'Description', 'class': 'form-control'}))
    starting_bid = forms.DecimalField(max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={'placeholder': '0.00', 'class': 'form-control'}))
    image_URL = forms.URLField(label="Image URL", required=False, widget=forms.URLInput(attrs={'placeholder': 'Optional', 'class': 'form-control'}))

class NewCommentForm(forms.Form):
    comment = forms.CharField(label="", widget=forms.Textarea(attrs={'placeholder': 'Comment...', 'class': 'form-control'}))

def index(request):
    # If a user is logged in, create a list of watchlist item id's to send to html.
    # This is used to display either an "add to" or a "remove from" watchlist button.
    # If no user is logged in, no watchlist options will be displayed.
    watchlist = []
    if request.user.is_authenticated:
        watchlist_data = request.user.watchlist.all()
        for item in watchlist_data:
            watchlist.append(item.listing.id)

    if request.method == "POST":

        if request.POST["browse_box"] == "active":
            listings = Listing.objects.filter(open=True)

        elif request.POST["browse_box"] == "closed":
            listings = Listing.objects.filter(open=False)

        elif request.POST["browse_box"] == "all":
            listings = Listing.objects.all()

        else:
            listings = Listing.objects.filter(category=request.POST["browse_box"]).filter(open=True)

        return render(request, "auctions/index.html", {
            "listings": listings,
            "watchlist": watchlist
        })

    else:
        return render(request, "auctions/index.html", {
            "listings": Listing.objects.filter(open=True),
            "watchlist": watchlist
        })

def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))

def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password, first_name=request.POST["first_name"], last_name=request.POST["last_name"])
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")

def new_listing(request):
    if request.method == "POST":
        # Validate form data.
        new_listing = Listing()
        new_listing_data = NewListingForm(request.POST)
        if new_listing_data.is_valid():
            new_listing.title = new_listing_data.cleaned_data["title"]
            new_listing.description = new_listing_data.cleaned_data["description"]
            new_listing.starting_bid = new_listing_data.cleaned_data["starting_bid"]
            new_listing.image_URL = new_listing_data.cleaned_data["image_URL"]
            new_listing.category = new_listing_data.cleaned_data["category"]
            new_listing.listed_datetime = datetime.datetime.now()
            new_listing.user = request.user
            if len(new_listing.image_URL) == 0:
                new_listing.image_URL = "https://thumbs.dreamstime.com/b/no-image-available-icon-photo-camera-flat-vector-illustration-132483141.jpg"
            new_listing.save()
        # Should I put an else statement here incase form data isn't valid?
        return HttpResponseRedirect(reverse("index"))

    else:
        return render(request, "auctions/new_listing.html",{
        "NewListingForm" : NewListingForm()
        })

def display_listing(request, listing_id):
    # Get listing and bidding data.
    listing = Listing.objects.get(pk=listing_id)
    bid_info = Bid.objects.filter(listing=listing_id)
    comments = Comment.objects.filter(listing=listing_id)

    # Determine the highest current bid. Use starting bid if there are no bids.
    if bid_info:
        highest_bid = (bid_info.last().bid)
    else:
        highest_bid = listing.starting_bid

    # If a user is logged in, create a list watchlist item id's to send to html.
    # This is used to display either an "add to" or a "remove from" watchlist button.
    # If no user is logged in, no watchlist or bidding options will be displayed.
    watchlist = []
    owner = False
    if request.user.is_authenticated:
        watchlist_data = request.user.watchlist.all()
        for item in watchlist_data:
            watchlist.append(item.listing.id)

        # Checking if logged-in user is also the owner of current listing.
        # If so, this allows an option to close the listing.
        if request.user.id == listing.user.id:
            owner = True

    if listing.open is True:
        return render(request, "auctions/display_open_listing.html", {
            "listing": listing,
            "watchlist": watchlist,
            "highest_bid": highest_bid,
            "bid_info": bid_info,
            "NewCommentForm": NewCommentForm(),
            "comments": comments,
            "owner": owner
            })

    elif listing.open is False:

        # Determine and communicate if current user is auctions winner.
        winner = False
        if bid_info.last().user_id == request.user.id:
            winner = True
        return render(request, "auctions/display_closed_listing.html",{
            "listing": listing,
            "watchlist": watchlist,
            "highest_bid": highest_bid,
            "bid_info": bid_info,
            "winner": winner,
        })

def add_to_watchlist(request, listing_id):
    # Add item to watchlist.
    new_watchlist_item = Watchlist()
    new_watchlist_item.user = request.user
    new_watchlist_item.listing = Listing.objects.get(pk=listing_id)

    # Make sure item isn't already in user's watchlist.
    # As far as i can see theres no need for this any more, but you never know.
    try:
        new_watchlist_item.save()
    except IntegrityError:
        message = "Item Already in Watchlist"
        return redirect("display_listing", listing_id = listing_id)

    # Here I would ideally like to redirect the user back where they came from,
    # so if they were viewing this particular listing it would take them back to display_listing,
    # but if they were viewing all listings it would take them to index, but i cant
    # figure out how to do this.
    return redirect("index")

def remove_from_watchlist(request, listing_id):
    # Remove item from a users watchlist.
    request.user.watchlist.get(listing_id = listing_id).delete()
    # Here I would ideally like to redirect the user back where they came from,
    # so if they were viewing this particular listing it would take them back to display_listing,
    # but if they were viewing all listings it would take them to index, but i cant
    # figure out how to do this.
    return redirect("index")

def display_watchlist(request):
    # Get watchlist info for current user.
    watchlist_info = request.user.watchlist.all()

    # Watchlist is a relational model, containing only foreign keys (the users id and the listing id)
    # A new list has to be created with the actual listing information to be displayed in html
    # (I think there might be a better way to do this, i dont know.)
    watchlist = []
    for item in watchlist_info:
        watchlist.append(Listing.objects.get(pk=item.listing_id))

    for choice in Listing.CATEGORY_CHOICES:
        print(choice[1])

    return render(request, "auctions/display_watchlist.html", {
    "watchlist" : watchlist,
    "choices" : Listing.CATEGORY_CHOICES
    })

def bid(request, listing_id):
    # Record any item bids in the Bid model of the database.
    if request.method == "POST":
        new_bid = Bid()
        new_bid.user = request.user
        new_bid.listing = Listing.objects.get(pk=listing_id)
        new_bid.bid_datetime = datetime.datetime.now()
        new_bid.bid = request.POST["bid"]
        new_bid.save()
        return HttpResponseRedirect(reverse("display_listing", args=(listing_id,)))

def close_listing(request, listing_id):
    # Close a listing by changing its open field to False.
    listing = Listing.objects.get(pk=listing_id)
    listing.open = False
    listing.save()
    return HttpResponseRedirect(reverse("display_listing", args=(listing_id,)))

def comment(request, listing_id):
    if request.method == "POST":
        new_comment = Comment()
        new_comment_data = NewCommentForm(request.POST)

        if new_comment_data.is_valid():
            new_comment.user = request.user
            new_comment.listing = Listing.objects.get(pk=listing_id)
            new_comment.text = new_comment_data.cleaned_data["comment"]
            new_comment.comment_datetime = datetime.datetime.now()
            new_comment.save()

        return HttpResponseRedirect(reverse("display_listing", args=(listing_id,)))
