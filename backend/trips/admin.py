from django.contrib import admin

from trips.models import Expense, ExpenseShare, Participant, Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("name", "destination", "start_date", "end_date", "created_at")
    readonly_fields = ("public_id", "admin_token_hash", "share_token_hash", "created_at")


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("name", "trip", "created_at")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "trip", "amount_cents", "category", "date", "payer")


@admin.register(ExpenseShare)
class ExpenseShareAdmin(admin.ModelAdmin):
    list_display = ("expense", "participant")
