$(function () {
    // Sidebar toggle for all screens
    const toggleSidebar = $("#toggleSidebar");
    const sidebar = $("#sidebar");
    const mainContent = $(".main-content");
    
    // Check saved sidebar state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarCollapsed && $(window).width() >= 992) {
        sidebar.addClass('collapsed');
        mainContent.addClass('expanded');
    }

    toggleSidebar.on("click", function (e) {
        e.preventDefault();
        
        if ($(window).width() >= 992) {
            // Desktop: toggle collapsed state
            sidebar.toggleClass("collapsed");
            mainContent.toggleClass("expanded");
            // Save state
            localStorage.setItem('sidebarCollapsed', sidebar.hasClass('collapsed'));
        } else {
            // Mobile: toggle show state
            sidebar.toggleClass("show");
        }
    });

    // Close sidebar when clicking outside on mobile
    $(document).on("click", function (e) {
        if ($(window).width() < 992) {
            if (!$(e.target).closest("#sidebar, #toggleSidebar").length) {
                sidebar.removeClass("show");
            }
        }
    });

    // Handle window resize
    $(window).on('resize', function() {
        if ($(window).width() >= 992) {
            sidebar.removeClass('show');
            // Restore desktop collapsed state
            const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            sidebar.toggleClass('collapsed', collapsed);
            mainContent.toggleClass('expanded', collapsed);
        } else {
            sidebar.removeClass('collapsed');
            mainContent.removeClass('expanded');
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
            'animation': `fadeIn 0.3s ease-out ${index * 0.04}s forwards`
        });
    });
});

// Global utility functions
function showAlert(type, message) {
    Swal.fire({
        icon: type,
        title: type.charAt(0).toUpperCase() + type.slice(1),
        text: message,
        confirmButtonText: 'OK'
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        Swal.fire({
            icon: 'success',
            title: 'Copied!',
            text: 'Text copied to clipboard',
            timer: 1500,
            showConfirmButton: false
        });
    }).catch(function(err) {
        console.error('Failed to copy text: ', err);
        showAlert('error', 'Failed to copy to clipboard');
    });
}
