function result = memga_search(action, varargin)
%MEMGA_SEARCH Internal. The two searches: exhaustive and genetic algorithm.
%
%   result = MEMGA_SEARCH('exhaustive', rule, n, set_size, labels, quotas)
%   result = MEMGA_SEARCH('ga', rule, groups, quotas, set_size, opts, progress)
%
%   QUOTAS is [] or a struct with the fields 'names' (cell array of group
%   names) and 'counts' (vacancies of each group).

switch action
    case 'exhaustive'
        result = exhaustive_search(varargin{:});
    case 'ga'
        result = run_ga(varargin{:});
    otherwise
        error('memga:internal', 'Unknown action ''%s''.', action);
end
end

% ======================================================================
% Exhaustive search: test every combination and rank them all.
% ======================================================================

function result = exhaustive_search(rule, n, set_size, labels, quotas)
total = nchoosek(n, set_size) * rule.n_combos;
if total > 2e7
    error('memga:tooLarge', ...
          'That would be %d evaluations, too many to test one by one. Use ''Method'', ''ga''.', total);
end
sets = nchoosek(1:n, set_size);
if ~isempty(quotas)
    keep = true(size(sets, 1), 1);
    for g = 1:numel(quotas.names)
        inside = strcmp(labels(sets), quotas.names{g});
        keep = keep & (sum(inside, 2) == quotas.counts(g));
    end
    sets = sets(keep, :);
end

n_sets = size(sets, 1);
scores = zeros(n_sets, 1);
chunk = 50000;
for first = 1:chunk:n_sets
    index = first:min(first + chunk - 1, n_sets);
    scores(index) = memga_rules('rate_means', rule, set_means(rule, sets(index, :)));
end

% sort is stable and nchoosek is in lexicographic order, so ties keep that order.
[~, order] = sort(-scores);
ranked = scores(order);
is_new = [true; diff(ranked) ~= 0];
position = cummax((1:n_sets)' .* is_new);

% When no set reaches tau, report the highest value found, to help choose tau.
max_value = NaN;
if ranked(1) == 0
    max_value = 0;
    for first = 1:chunk:n_sets
        index = first:min(first + chunk - 1, n_sets);
        values = memga_rules('values', rule, set_means(rule, sets(index, :)));
        max_value = max(max_value, max(values(:)));
    end
end
result = struct('sets', sets(order, :), 'score', ranked, 'position', position, 'max_value', max_value);
end

function means = set_means(rule, picked)
% Average performance of each set (one per row of PICKED) on each criterion.
sums = zeros(size(picked, 1), size(rule.payment, 2));
for j = 1:size(picked, 2)
    sums = sums + rule.payment(picked(:, j), :);
end
means = sums / size(picked, 2);
end

% ======================================================================
% Genetic algorithm with a strong mutation.
% ======================================================================

function result = run_ga(rule, groups, quotas, set_size, opts, progress)
n = size(rule.payment, 1);
if isempty(quotas)
    if set_size < 1
        error('memga:badSize', 'The set needs at least 1 alternative.');
    end
    if set_size > n
        error('memga:badSize', 'The set asks for %d alternatives, but the data has only %d.', set_size, n);
    end
    labels = repmat({'*'}, 1, n);
    names = {'*'};
    counts = set_size;
else
    labels = groups;
    keep = quotas.counts > 0;
    names = quotas.names(keep);
    counts = quotas.counts(keep);
end
pools = cell(1, numel(names));
for g = 1:numel(names)
    pools{g} = find(strcmp(labels, names{g}));
    if counts(g) > numel(pools{g})
        error('memga:badQuotas', 'Group %s has %d alternatives, and %d were requested.', ...
              names{g}, numel(pools{g}), counts(g));
    end
end
ctx = struct('rule', rule, 'labels', {labels}, 'names', {names}, 'counts', counts, ...
             'pools', {pools}, 'opts', opts);

state = warning('off', 'all');
possible = 1;
for g = 1:numel(names)
    possible = possible * nchoosek(numel(pools{g}), counts(g));
end
warning(state);
target = min(opts.population, possible);

st = struct('teams', {{}}, 'score', zeros(0, 1), 'tie', zeros(0, 1), ...
            'seen', containers.Map('KeyType', 'char', 'ValueType', 'logical'));
initial = containers.Map('KeyType', 'char', 'ValueType', 'logical');
while numel(st.teams) < target
    team = pick(ctx, 1:n);
    key = team_key(team);
    if ~isKey(initial, key)
        initial(key) = true;
        rated = rate_team(ctx, team);
        st.teams{end + 1} = team;
        st.score(end + 1, 1) = rated.score;
        st.tie(end + 1, 1) = rated.tie;
    end
end
st = sort_population(st);
for k = 1:numel(st.teams)
    st.seen(team_key(st.teams{k})) = true;
end

best = top(st);
stagnant = 0;
mutations = 0;
history = zeros(opts.iterations, 1);
for iteration = 1:opts.iterations
    child = new_child(ctx, st);
    st = replace_worst(st, rate_team(ctx, child));
    leader = top(st);
    if is_better(leader, best)
        best = leader;
        stagnant = 0;
    else
        stagnant = stagnant + 1;
        if stagnant == opts.stagnation
            [best, st] = mutate(ctx, st, best);
            stagnant = 0;
            mutations = mutations + 1;
            if mod(mutations, opts.climb_every) == 0
                [best, st] = strong_mutation(ctx, st, best);
            end
        end
    end
    history(iteration) = best.score;
    if progress && (mod(iteration, 100) == 0 || iteration == opts.iterations)
        fprintf('\rGenetic algorithm: %3d%%', round(100 * iteration / opts.iterations));
    end
end
if progress
    fprintf('\n');
end
max_value = NaN;
if best.score == 0
    means = mean(rule.payment(best.team, :), 1);
    max_value = max(memga_rules('values', rule, means));
end
result = struct('team', best.team, 'score', best.score, 'history', history, 'max_value', max_value);
end

function key = team_key(team)
key = sprintf('%d,', team);
end

function yes = is_better(a, b)
% True when a is better than b, comparing the score first and the tie-breaker second.
yes = a.score > b.score || (a.score == b.score && a.tie > b.tie);
end

function rated = rate_team(ctx, team)
rated = memga_rules('rate', ctx.rule, team);
end

function g = group_index(ctx, member)
g = find(strcmp(ctx.names, ctx.labels{member}), 1);
end

% Draws the alternatives of each group among the candidates.
function team = pick(ctx, candidates)
team = [];
for g = 1:numel(ctx.names)
    pool = candidates(strcmp(ctx.labels(candidates), ctx.names{g}));
    team = [team, pool(randperm(numel(pool), ctx.counts(g)))]; %#ok<AGROW>
end
team = sort(team);
end

function st = sort_population(st)
[~, order] = sortrows([st.score, st.tie]);
st.teams = st.teams(order);
st.score = st.score(order);
st.tie = st.tie(order);
end

function best = top(st)
last = numel(st.teams);
best = struct('score', st.score(last), 'tie', st.tie(last), 'team', st.teams{last});
end

function st = replace_worst(st, rated)
st.teams{end + 1} = rated.team;
st.score(end + 1, 1) = rated.score;
st.tie(end + 1, 1) = rated.tie;
st = sort_population(st);
st.teams(1) = [];
st.score(1) = [];
st.tie(1) = [];
% 'seen' holds every set that has been in the population, so adding the new one is enough.
st.seen(team_key(rated.team)) = true;
end

function child = crossover(ctx, st)
parents = randi(numel(st.teams), 1, 2);
child = pick(ctx, union(st.teams{parents(1)}, st.teams{parents(2)}));
end

function child = new_child(ctx, st)
child = crossover(ctx, st);
if isKey(st.seen, team_key(child))
    current = cellfun(@team_key, st.teams, 'UniformOutput', false);
    % The limit avoids an endless loop when the population has converged.
    for attempt = 1:1000
        child = crossover(ctx, st);
        if ~ismember(team_key(child), current)
            break
        end
    end
end
end

function [best, st] = mutate(ctx, st, best)
eligible = find(ismember(ctx.labels, ctx.names));
untested = setdiff(eligible, best.team);
for attempt = 1:ctx.opts.mutation_attempts
    if isempty(untested)
        break
    end
    newcomer = untested(randi(numel(untested)));
    untested(untested == newcomer) = [];
    slots = find(strcmp(ctx.labels(best.team), ctx.labels{newcomer}));
    mutant = best.team;
    mutant(slots(randi(numel(slots)))) = newcomer;
    rated = rate_team(ctx, mutant);
    % The better set becomes the champion without entering the population.
    if is_better(rated, best)
        best = rated;
        return
    end
    st = replace_worst(st, rated);
end
end

% Swaps kick_size alternatives at once, each for another of the same group.
function team = kick(ctx, team)
spare = cell(size(ctx.pools));
for g = 1:numel(spare)
    spare{g} = setdiff(ctx.pools{g}, team);
end
slots = [];
for s = 1:numel(team)
    if ~isempty(spare{group_index(ctx, team(s))})
        slots(end + 1) = s; %#ok<AGROW>
    end
end
if isempty(slots)
    return
end
chosen = slots(randperm(numel(slots), min(ctx.opts.kick_size, numel(slots))));
for slot = chosen
    g = group_index(ctx, team(slot));
    pool = spare{g};
    % A group with few spare alternatives can run out before kick_size swaps.
    if ~isempty(pool)
        index = randi(numel(pool));
        team(slot) = pool(index);
        pool(index) = [];
        spare{g} = pool;
    end
end
team = sort(team);
end

% Swaps one alternative at a time, inside its group, while the score goes up.
function best = climb(ctx, team)
best = rate_team(ctx, team);
improved = true;
while improved
    improved = false;
    for slot = 1:numel(team)
        others = team([1:slot - 1, slot + 1:end]);
        candidates = setdiff(ctx.pools{group_index(ctx, team(slot))}, team);
        if isempty(candidates)
            continue
        end
        base = sum(ctx.rule.payment(others, :), 1);
        means = (ctx.rule.payment(candidates, :) + repmat(base, numel(candidates), 1)) / numel(team);
        [score, tie] = memga_rules('rate_means', ctx.rule, means);
        [~, order] = sortrows([-score, -tie]);
        first = order(1);
        challenger = struct('score', score(first), 'tie', tie(first));
        if is_better(challenger, best)
            team(slot) = candidates(first);
            best = struct('score', challenger.score, 'tie', challenger.tie, 'team', sort(team));
            improved = true;
        end
    end
end
end

function [best, st] = strong_mutation(ctx, st, best)
rated = climb(ctx, kick(ctx, best.team));
if is_better(best, rated)
    return
end
% Copies of the same set in the population would lock the crossover in new_child.
current = cellfun(@team_key, st.teams, 'UniformOutput', false);
if ~ismember(team_key(rated.team), current)
    st = replace_worst(st, rated);
end
best = rated;
end
