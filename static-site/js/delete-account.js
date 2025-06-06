// JavaScript for delete account functionality
document.addEventListener('DOMContentLoaded', function() {
    const deleteForm = document.getElementById('deleteAccountForm');
    const submitBtn = document.getElementById('submitBtn');
    const successMessage = document.getElementById('successMessage');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');

    deleteForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form data
        const email = document.getElementById('email').value.trim();
        const reason = document.getElementById('reason').value.trim();
        
        // Validate email
        if (!email) {
            showError('Please enter your email address.');
            return;
        }
        
        if (!isValidEmail(email)) {
            showError('Please enter a valid email address.');
            return;
        }
        
        // Disable submit button and show loading state
        setLoading(true);
        
        try {
            // Prepare the request data
            const requestData = {
                content: `Account Deletion Request from: ${email}${reason ? `\n\nReason: ${reason}` : ''}`
            };
            
            // Send POST request to the API
            const response = await fetch('https://api.assistlyai.space/api/v1/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            if (response.ok) {
                // Success - show success message and hide form
                showSuccess();
                deleteForm.style.display = 'none';
            } else {
                // API returned an error
                const errorData = await response.json().catch(() => ({}));
                const errorMsg = errorData.detail || errorData.message || 'Failed to submit deletion request. Please try again.';
                showError(errorMsg);
            }
        } catch (error) {
            // Network or other error
            console.error('Error submitting deletion request:', error);
            showError('Network error. Please check your connection and try again.');
        } finally {
            // Re-enable submit button
            setLoading(false);
        }
    });
    
    function setLoading(loading) {
        submitBtn.disabled = loading;
        submitBtn.textContent = loading ? 'Submitting Request...' : 'Request Account Deletion';
    }
    
    function showSuccess() {
        hideMessages();
        successMessage.style.display = 'block';
        successMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    function showError(message) {
        hideMessages();
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    function hideMessages() {
        successMessage.style.display = 'none';
        errorMessage.style.display = 'none';
    }
    
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // Clear messages when user starts typing again
    document.getElementById('email').addEventListener('input', hideMessages);
    document.getElementById('reason').addEventListener('input', hideMessages);
});
