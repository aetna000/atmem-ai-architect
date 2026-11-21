Inline chat details
===================

Owner replaced chat question-mark popovers with an explicit More details button. It replaces the preview with the complete response in the same message; Less details restores the preview. The Review action is Complete →; this navigates to Delivery without declaring failed or missing checks passed. Redundant Delivery/Checks help icons were removed.

Validation: npm run build passed. Both browser scripts passed against http://127.0.0.1:5298 using isolated contexts and API fixtures: scripts/chat-layout-check.mjs and scripts/review-delivery-check.mjs. No model call, owner data write, cloud access, backend restart or release qualification.
