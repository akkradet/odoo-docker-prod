$(document).ready(function() {
    $('#slideBanner').owlCarousel({
        autoplay: true,
        margin:10,
        nav:true,
        loop:true,
        paginationSpeed : 10000,
        singleItem:true,
        pagination: true,
        lazyLoad : true,
        slideSpeed : 10000,
        autoplayTimeout: 10000,
        transitionStyle:"fade",
        navText: ['<i class="fa fa-angle-left"></i>', '<i class="fa fa-angle-right"></i>'],
        dots: false,
        responsive:{
            0:{
                items:1
            },
            600:{
                items:1
            },
            1000:{
                items:1
            }
        }
    });
});