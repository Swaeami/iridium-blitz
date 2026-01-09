$(function () {
    const sidebar = $("#sidebar");
    const toggleSidebar = $("#toggleSidebar");
    
    // Create backdrop for mobile
    $('body').append('<div class="sidebar-backdrop" id="sidebarBackdrop"></div>');
    const backdrop = $("#sidebarBackdrop");

    // Toggle sidebar on mobile
    toggleSidebar.on("click", function (e) {
        e.preventDefault();
        if ($(window).width() < 992) {
            sidebar.toggleClass("mobile-show");
            backdrop.toggleClass("show");
        }
    });

    // Close sidebar when clicking backdrop
    backdrop.on("click", function () {
        sidebar.removeClass("mobile-show");
        backdrop.removeClass("show");
    });

    // Handle window resize
    $(window).on('resize', function() {
        if ($(window).width() >= 992) {
            sidebar.removeClass("mobile-show");
            backdrop.removeClass("show");
        }
    });

    // Update notification handling
    initUpdateNotification();

    function initUpdateNotification() {
        const showChangelogBtn = $('#showChangelog');
        const changelogContent = $('#changelogContent');
        const closeUpdateBar = $('#closeUpdateBar');
        const remindLater = $('#remindLater');
        const skipVersion = $('#skipVersion');
        const viewRelease = $('#viewRelease');

        showChangelogBtn.on('click', function(e) {
            e.preventDefault();
            changelogContent.slideToggle(200);
            $(this).find('i').toggleClass('fa-chevron-down fa-chevron-up');
        });

        closeUpdateBar.on('click', function() {
            $('#updateBar').slideUp(200);
        });

        remindLater.on('click', function(e) {
            e.preventDefault();
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            localStorage.setItem('updateRemindDate', tomorrow.toISOString());
            $('#updateBar').slideUp(200);
        });

        skipVersion.on('click', function(e) {
            e.preventDefault();
            const currentVersion = $('#updateBar').data('new-version');
            if (currentVersion) {
                localStorage.setItem('skippedVersion', currentVersion);
            }
            $('#updateBar').slideUp(200);
        });

        viewRelease.on('click', function(e) {
            e.preventDefault();
            window.open('https://github.com/Swaeami/iridium-blitz/releases', '_blank');
        });
    }

    // Add fade-in animation to cards
    $('.card, .stat-card, .info-box, .small-box').each(function(index) {
        $(this).css({
            'opacity': '0',
            'animation': `fadeIn 0.25s ease-out ${index * 0.03}s forwards`
        });
    });
});

// Toast notification helper
function showToast(type, title, timer = 3000) {
    Swal.fire({
        icon: type,
        title: title,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: timer,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        }
    });
}

// Global utility functions
function showAlert(type, message) {
    showToast(type, message);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('success', 'Copied to clipboard!', 1500);
    }).catch(function(err) {
        console.error('Failed to copy text: ', err);
        showToast('error', 'Failed to copy');
    });
}
