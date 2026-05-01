/**
 * SweetAlert Utilities - Randini Auto Garage
 * ==========================================
 * Utility functions for displaying beautiful alerts and notifications
 * using SweetAlert2 library.
 */

// SweetAlert2 CDN - Include this in your base template
// <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

class SweetAlertUtils {
    
    /**
     * Show success notification
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {function} callback - Optional callback function
     */
    static success(title, message, callback = null) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'success',
            confirmButtonColor: '#800000',
            confirmButtonText: 'Great!',
            timer: 3000,
            timerProgressBar: true,
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (callback && result.isConfirmed) {
                callback();
            }
        });
    }

    /**
     * Show error notification
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {function} callback - Optional callback function
     */
    static error(title, message, callback = null) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'error',
            confirmButtonColor: '#800000',
            confirmButtonText: 'OK',
            showClass: {
                popup: 'animate__animated animate__shakeX'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (callback && result.isConfirmed) {
                callback();
            }
        });
    }

    /**
     * Show warning notification
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {function} callback - Optional callback function
     */
    static warning(title, message, callback = null) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'warning',
            confirmButtonColor: '#ffc107',
            confirmButtonText: 'Got it!',
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (callback && result.isConfirmed) {
                callback();
            }
        });
    }

    /**
     * Show info notification
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {function} callback - Optional callback function
     */
    static info(title, message, callback = null) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'info',
            confirmButtonColor: '#17a2b8',
            confirmButtonText: 'OK',
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (callback && result.isConfirmed) {
                callback();
            }
        });
    }

    /**
     * Show confirmation dialog
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {string} confirmText - Confirm button text
     * @param {string} cancelText - Cancel button text
     * @param {function} onConfirm - Function to call on confirm
     * @param {function} onCancel - Function to call on cancel
     */
    static confirm(title, message, confirmText = 'Yes, do it!', cancelText = 'Cancel', onConfirm = null, onCancel = null) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#800000',
            cancelButtonColor: '#6c757d',
            confirmButtonText: confirmText,
            cancelButtonText: cancelText,
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (result.isConfirmed && onConfirm) {
                onConfirm();
            } else if (result.isDismissed && onCancel) {
                onCancel();
            }
        });
    }

    /**
     * Show loading dialog
     * @param {string} title - Loading title
     * @param {string} message - Loading message
     * @returns {object} SweetAlert instance for closing
     */
    static loading(title = 'Loading...', message = 'Please wait...') {
        return Swal.fire({
            title: title,
            text: message,
            allowOutsideClick: false,
            allowEscapeKey: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    }

    /**
     * Close loading dialog
     */
    static closeLoading() {
        Swal.close();
    }

    /**
     * Show toast notification (small popup)
     * @param {string} title - Toast title
     * @param {string} message - Toast message
     * @param {string} icon - Icon type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    static toast(title, message, icon = 'success', duration = 3000) {
        const Toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: duration,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.addEventListener('mouseenter', Swal.stopTimer)
                toast.addEventListener('mouseleave', Swal.resumeTimer)
            }
        });

        Toast.fire({
            icon: icon,
            title: title,
            text: message
        });
    }

    /**
     * Show form dialog with input
     * @param {string} title - Dialog title
     * @param {string} message - Dialog message
     * @param {string} inputType - Input type (text, email, password, etc.)
     * @param {string} inputPlaceholder - Input placeholder
     * @param {function} onConfirm - Function to call on confirm
     */
    static prompt(title, message, inputType = 'text', inputPlaceholder = 'Enter value...', onConfirm = null) {
        Swal.fire({
            title: title,
            text: message,
            input: inputType,
            inputPlaceholder: inputPlaceholder,
            showCancelButton: true,
            confirmButtonColor: '#800000',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'Submit',
            cancelButtonText: 'Cancel',
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (result.isConfirmed && onConfirm) {
                onConfirm(result.value);
            }
        });
    }

    /**
     * Show success with redirect
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {string} redirectUrl - URL to redirect to
     * @param {number} delay - Delay before redirect (ms)
     */
    static successRedirect(title, message, redirectUrl, delay = 2000) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'success',
            confirmButtonColor: '#800000',
            confirmButtonText: 'Continue',
            timer: delay,
            timerProgressBar: true,
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            window.location.href = redirectUrl;
        });
    }

    /**
     * Show error with reload option
     * @param {string} title - Alert title
     * @param {string} message - Alert message
     * @param {boolean} showReload - Whether to show reload button
     */
    static errorReload(title, message, showReload = true) {
        Swal.fire({
            title: title,
            text: message,
            icon: 'error',
            confirmButtonColor: '#800000',
            confirmButtonText: showReload ? 'Reload Page' : 'OK',
            showClass: {
                popup: 'animate__animated animate__shakeX'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (result.isConfirmed && showReload) {
                window.location.reload();
            }
        });
    }

    /**
     * Show booking confirmation
     * @param {string} serviceType - Type of service booked
     * @param {string} date - Booking date
     * @param {function} onViewDetails - Function to view booking details
     */
    static bookingConfirmation(serviceType, date, onViewDetails = null) {
        Swal.fire({
            title: 'Booking Confirmed!',
            html: `
                <div style="text-align: left; padding: 20px;">
                    <p><strong>Service:</strong> ${serviceType}</p>
                    <p><strong>Date:</strong> ${date}</p>
                    <p style="color: #28a745; margin-top: 15px;">
                        <i class="bi bi-check-circle-fill"></i> Your booking has been confirmed successfully!
                    </p>
                </div>
            `,
            icon: 'success',
            confirmButtonColor: '#800000',
            confirmButtonText: 'View Details',
            showCancelButton: true,
            cancelButtonText: 'Close',
            cancelButtonColor: '#6c757d',
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (result.isConfirmed && onViewDetails) {
                onViewDetails();
            }
        });
    }

    /**
     * Show payment success
     * @param {string} amount - Payment amount
     * @param {string} paymentMethod - Payment method used
     * @param {function} onViewReceipt - Function to view receipt
     */
    static paymentSuccess(amount, paymentMethod, onViewReceipt = null) {
        Swal.fire({
            title: 'Payment Successful!',
            html: `
                <div style="text-align: left; padding: 20px;">
                    <p><strong>Amount:</strong> KSh ${amount}</p>
                    <p><strong>Method:</strong> ${paymentMethod}</p>
                    <p style="color: #28a745; margin-top: 15px;">
                        <i class="bi bi-check-circle-fill"></i> Your payment has been processed successfully!
                    </p>
                </div>
            `,
            icon: 'success',
            confirmButtonColor: '#800000',
            confirmButtonText: 'View Receipt',
            showCancelButton: true,
            cancelButtonText: 'Close',
            cancelButtonColor: '#6c757d',
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (result.isConfirmed && onViewReceipt) {
                onViewReceipt();
            }
        });
    }

    /**
     * Show registration success
     * @param {string} customerName - Customer name
     * @param {function} onLogin - Function to redirect to login
     */
    static registrationSuccess(customerName, onLogin = null) {
        Swal.fire({
            title: 'Registration Successful!',
            html: `
                <div style="text-align: center; padding: 20px;">
                    <p style="font-size: 1.1rem;">Welcome to Randini Auto Garage, <strong>${customerName}</strong>!</p>
                    <p style="color: #28a745; margin-top: 15px;">
                        <i class="bi bi-envelope-fill"></i> A welcome email has been sent to your email address.
                    </p>
                    <p style="margin-top: 15px;">You can now log in and book your first service!</p>
                </div>
            `,
            icon: 'success',
            confirmButtonColor: '#800000',
            confirmButtonText: 'Go to Login',
            showClass: {
                popup: 'animate__animated animate__fadeInDown'
            },
            hideClass: {
                popup: 'animate__animated animate__fadeOutUp'
            }
        }).then((result) => {
            if (result.isConfirmed && onLogin) {
                onLogin();
            }
        });
    }
}

// Auto-initialize SweetAlert when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if SweetAlert2 is loaded
    if (typeof Swal === 'undefined') {
        console.warn('SweetAlert2 is not loaded. Please include the SweetAlert2 CDN.');
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SweetAlertUtils;
}
