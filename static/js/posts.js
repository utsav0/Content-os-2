(() => {
    'use strict';

    const CONFIG = { POSTS_PER_PAGE: 20, SCROLL_THRESHOLD: 100 };

    let state = {
        offset: 0,
        isLoading: false,
        sortBy: 'post_datetime',
        sortOrder: 'desc',
        filters: {}
    };

    const DOM = {
        postsContainer: document.getElementById('posts-container'),
        loading: document.getElementById('loading'),
        filterForm: document.querySelector('.filter-form'),
        filterBtn: document.getElementById('filter-button'),
        clearFiltersBtn: document.getElementById('clear-filters'),
        sortButtons: {
            impressions: document.getElementById('sort-impressions'),
            likes: document.getElementById('sort-likes'),
            comments: document.getElementById('sort-comments'),
            date: document.getElementById('sort-dates'),
            latest_date: document.getElementById('sort-latest-dates'),
            ctr: document.getElementById('sort-ctr'),
            clicks: document.getElementById('sort-clicks')
        },
        filterInputs: {
            impressions_min: document.getElementById('impressions-from'),
            impressions_max: document.getElementById('impressions-to'),
            likes_min: document.getElementById('likes-from'),
            likes_max: document.getElementById('likes-to'),
            comments_min: document.getElementById('comments-from'),
            comments_max: document.getElementById('comments-to'),
            date_from: document.getElementById('date-from'),
            date_to: document.getElementById('date-to'),
            latest_date_from: document.getElementById('latest-date-from'),
        latest_date_to: document.getElementById('latest-date-to')
        }
    };

    function fetchPosts() {
        state.isLoading = true;
        DOM.loading.style.display = 'block';

        const params = new URLSearchParams({
            offset: state.offset,
            limit: CONFIG.POSTS_PER_PAGE,
            sort_by: state.sortBy,
            sort_order: state.sortOrder,
            ...state.filters
        });

        return fetch(`/api/posts?${params.toString()}`)
            .then(res => res.json())
            .then(posts => {
                posts.forEach(post => {
                    const postEl = document.createElement('div');
                    postEl.classList.add('post');

                    const caption = document.createElement('a');
                    caption.href = `/post/${post.post_id}`;
                    caption.classList.add('post__caption', 'hoverable-white');
                    caption.textContent = post.caption;

                    const stats = document.createElement('div');
                    stats.classList.add('post__stats');
                    stats.innerHTML = `
                        <span><i class="fas fa-eye"></i> ${post.impressions !== null ? post.impressions : '-'}</span>
                        <span><i class="fas fa-heart"></i> ${post.likes !== null ? post.likes : '-'}</span>
                        <span><i class="fas fa-comment"></i> ${post.comments !== null ? post.comments : '-'}</span>
                        <span><i class="fa-solid fa-rocket"></i> ${post.main_ebook_ctr !== null ? post.main_ebook_ctr : '-'}</span>
                        <span><i class="fa-solid fa-mouse-pointer"></i> ${post.main_ebook_clicks !== null ? post.main_ebook_clicks : '-'}</span>
                        <span><i class="fa-solid fa-calendar"></i> ${post.post_datetime}</span>
                        <span><i class="fa-solid fa-clock"></i> ${post.latest_post_datetime}</span>
                    `;

                    postEl.appendChild(caption);
                    postEl.appendChild(stats);
                    DOM.postsContainer.appendChild(postEl);
                });

                state.offset += CONFIG.POSTS_PER_PAGE;
                state.isLoading = false;
                DOM.loading.style.display = 'none';
            })
            .catch(err => {
                console.error('Error fetching posts:', err);
                state.isLoading = false;
                DOM.loading.style.display = 'none';
            });
    }

    function clearPosts() {
        const posts = DOM.postsContainer.querySelectorAll('.post');
        posts.forEach(p => p.remove());
    }

    function handleFilterSubmit(e) {
        e.preventDefault();
        state.filters = {};
        for (const key in DOM.filterInputs) {
            const val = DOM.filterInputs[key].value;
            if (val) state.filters[key] = val;
        }
        state.offset = 0;
        clearPosts();
        fetchPosts();
        DOM.filterForm.classList.add('hidden');
    }

    function handleClearFilters() {
        for (const input of Object.values(DOM.filterInputs)) input.value = '';
        state.filters = {};
        state.offset = 0;
        clearPosts();
        fetchPosts();
        DOM.filterForm.classList.add('hidden');
    }

    function setupSortButton(buttonEl, column) {
        buttonEl.addEventListener('click', () => {
            if (state.sortBy === column) state.sortOrder = state.sortOrder === 'desc' ? 'asc' : 'desc';
            else { state.sortBy = column; state.sortOrder = 'desc'; }
            state.offset = 0;
            clearPosts();
            fetchPosts();
        });
    }

    function setupFilterToggle() {
        DOM.filterBtn.addEventListener('click', e => {
            e.stopPropagation();
            DOM.filterForm.classList.toggle('hidden');
        });
        DOM.filterForm.addEventListener('click', e => e.stopPropagation());
        document.addEventListener('click', e => {
            if (!DOM.filterForm.contains(e.target) && e.target !== DOM.filterBtn) {
                DOM.filterForm.classList.add('hidden');
            }
        });
    }

    function init() {
        window.addEventListener('scroll', () => {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - CONFIG.SCROLL_THRESHOLD && !state.isLoading) {
                fetchPosts();
            }
        });

        DOM.filterForm.addEventListener('submit', handleFilterSubmit);
        DOM.clearFiltersBtn.addEventListener('click', handleClearFilters);

        setupSortButton(DOM.sortButtons.impressions, 'impressions');
        setupSortButton(DOM.sortButtons.likes, 'likes');
        setupSortButton(DOM.sortButtons.comments, 'comments');
        setupSortButton(DOM.sortButtons.date, 'post_datetime');
        setupSortButton(DOM.sortButtons.latest_date, 'latest_post_datetime');
        setupSortButton(DOM.sortButtons.ctr, 'main_ebook_ctr');
        setupSortButton(DOM.sortButtons.clicks, 'main_ebook_clicks');

        setupFilterToggle();
        fetchPosts();
    }

    document.addEventListener('DOMContentLoaded', init);

})();
