(() => {
    'use strict';

    const CONFIG = { TOPICS_PER_PAGE: 20, SCROLL_THRESHOLD: 100 };

    let state = {
        offset: 0,
        isLoading: false,
        sortBy: 'last_posted',
        sortOrder: 'desc',
        filters: {}
    };

    const DOM = {
        topicsContainer: document.getElementById('topics-container'),
        loading: document.getElementById('loading'),
        filterForm: document.querySelector('.filter-form'),
        filterBtn: document.getElementById('filter-button'),
        clearFiltersBtn: document.getElementById('clear-filters'),
        sortButtons: {
            post_count: document.getElementById('sort-post-count'),
            impressions: document.getElementById('sort-impressions'),
            likes: document.getElementById('sort-likes'),
            comments: document.getElementById('sort-comments'),
            last_posted: document.getElementById('sort-last-posted')
        },
        filterInputs: {
            impressions_min: document.getElementById('impressions-from'),
            impressions_max: document.getElementById('impressions-to'),
            likes_min: document.getElementById('likes-from'),
            likes_max: document.getElementById('likes-to'),
            comments_min: document.getElementById('comments-from'),
            comments_max: document.getElementById('comments-to'),
            date_from: document.getElementById('date-from'),
            date_to: document.getElementById('date-to')
        }
    };

    function fetchTopics() {
        state.isLoading = true;
        DOM.loading.style.display = 'block';

        const params = new URLSearchParams({
            offset: state.offset,
            limit: CONFIG.TOPICS_PER_PAGE,
            sort_by: state.sortBy,
            sort_order: state.sortOrder,
            ...state.filters
        });

        return fetch(`/api/topics-list?${params.toString()}`)
            .then(res => res.json())
            .then(topics => {
                topics.forEach(topic => {
                    const row = document.createElement('div');
                    row.classList.add('data-row');

                    const name = document.createElement('a');
                    name.href = `/topic/${topic.id}`;
                    name.classList.add('data-row__title', 'hoverable-white', 'nulled-link');
                    name.textContent = topic.name;

                    const stats = document.createElement('div');
                    stats.classList.add('data-row__stats');
                    stats.innerHTML = `
                        <span><i class="fas fa-hashtag"></i> ${topic.post_count}</span>
                        <span><i class="fas fa-eye"></i> ${topic.median_impressions !== null ? topic.median_impressions : '-'}</span>
                        <span><i class="fas fa-heart"></i> ${topic.median_likes !== null ? topic.median_likes : '-'}</span>
                        <span><i class="fas fa-comment"></i> ${topic.median_comments !== null ? topic.median_comments : '-'}</span>
                        <span><i class="fa-solid fa-calendar"></i> ${topic.last_posted || '-'}</span>
                    `;

                    row.appendChild(name);
                    row.appendChild(stats);
                    DOM.topicsContainer.appendChild(row);
                });

                state.offset += CONFIG.TOPICS_PER_PAGE;
                state.isLoading = false;
                DOM.loading.style.display = 'none';
            })
            .catch(err => {
                console.error('Error fetching topics:', err);
                state.isLoading = false;
                DOM.loading.style.display = 'none';
            });
    }

    function clearTopics() {
        const rows = DOM.topicsContainer.querySelectorAll('.data-row');
        rows.forEach(r => r.remove());
    }

    function handleFilterSubmit(e) {
        e.preventDefault();
        state.filters = {};
        for (const key in DOM.filterInputs) {
            const val = DOM.filterInputs[key].value;
            if (val) state.filters[key] = val;
        }
        state.offset = 0;
        clearTopics();
        fetchTopics();
        DOM.filterForm.classList.add('hidden');
    }

    function handleClearFilters() {
        for (const input of Object.values(DOM.filterInputs)) input.value = '';
        state.filters = {};
        state.offset = 0;
        clearTopics();
        fetchTopics();
        DOM.filterForm.classList.add('hidden');
    }

    function setupSortButton(buttonEl, column) {
        buttonEl.addEventListener('click', () => {
            if (state.sortBy === column) state.sortOrder = state.sortOrder === 'desc' ? 'asc' : 'desc';
            else { state.sortBy = column; state.sortOrder = 'desc'; }
            state.offset = 0;
            clearTopics();
            fetchTopics();
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
                fetchTopics();
            }
        });

        DOM.filterForm.addEventListener('submit', handleFilterSubmit);
        DOM.clearFiltersBtn.addEventListener('click', handleClearFilters);

        setupSortButton(DOM.sortButtons.post_count, 'post_count');
        setupSortButton(DOM.sortButtons.impressions, 'median_impressions');
        setupSortButton(DOM.sortButtons.likes, 'median_likes');
        setupSortButton(DOM.sortButtons.comments, 'median_comments');
        setupSortButton(DOM.sortButtons.last_posted, 'last_posted');

        setupFilterToggle();
        fetchTopics();
    }

    document.addEventListener('DOMContentLoaded', init);

})();
