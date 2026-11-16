"""Compatibility facade for the notification module's focused services."""

from app.core.notification_catalog import (
    ADMIN_ROLE_CODE, DELIVERY_NOTIFICATION_TYPES, FLETE_RETURN_NOTIFICATION_TYPES,
    NOTIFICATION_TYPES, TEST_NOTIFICATION_TYPES, build_notification_action_path, utc_now,
)
from app.services.notification_query_service import (
    get_notification_detail, get_notification_report_summary, get_notification_summary,
    list_notifications, mark_all_notifications_read, mark_notification_read, resolve_notification,
)
from app.services.notification_sync_service import (
    create_notification_for_user, create_notifications_for_roles, reconcile_user_notification_eligibility,
    resolve_notifications_by_reference, sync_boutique_stock_notification,
    sync_flete_max_outputs_notification, sync_flete_return_notifications_for_output,
    sync_material_preparation_notification_for_test, sync_order_delivery_notifications_for_order,
    sync_test_schedule_notifications_for_test, sync_workshop_stock_notification,
    sync_order_test_notifications_for_order,
)
from app.services.notification_delivery_service import (
    claim_desktop_notifications, get_notification_preferences, set_notification_preferences,
)
from app.services.notification_email_service import (
    create_email_failure_notification, resolve_email_failure_notifications,
    retry_email_notification, send_welcome_email_with_tracking, queue_welcome_email,
)
