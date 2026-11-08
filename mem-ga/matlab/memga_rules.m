function varargout = memga_rules(action, varargin)
%MEMGA_RULES Internal. Normalisation, group weights and the two scoring rules.
%
%   A rule receives the average performance of a set on each criterion and
%   returns a score (the share of criteria combinations in which the set
%   reaches tau) and a tie-breaker (the average of min(value, tau)).
%
%   Actions: 'normalize', 'group_weights', 'complementarity', 'build',
%            'values', 'rate_means', 'rate'.

switch action
    case 'normalize',       [varargout{1:nargout}] = normalize_values(varargin{:});
    case 'group_weights',   [varargout{1:nargout}] = group_weights(varargin{:});
    case 'complementarity', [varargout{1:nargout}] = complementarity_from_data(varargin{:});
    case 'build',           [varargout{1:nargout}] = build_rule(varargin{:});
    case 'values',          [varargout{1:nargout}] = rule_values(varargin{:});
    case 'rate_means',      [varargout{1:nargout}] = rule_rate_means(varargin{:});
    case 'rate',            [varargout{1:nargout}] = rule_rate(varargin{:});
    otherwise
        error('memga:internal', 'Unknown action ''%s''.', action);
end
end

function out = normalize_values(values, direction)
% Equation 3.1 of the thesis: each criterion goes from 0 to 1, and 1 is the best.
high = max(values, [], 1);
low = min(values, [], 1);
benefit = direction >= 1;
best = low;   best(benefit) = high(benefit);
worst = high; worst(benefit) = low(benefit);
spread = best - worst;
spread(spread == 0) = 1;
out = (values - repmat(worst, size(values, 1), 1)) ./ repmat(spread, size(values, 1), 1);
end

function weights = group_weights(values, groups, direction)
% How much each group does each criterion above the other groups, in standard
% deviations. Every criterion starts at 1, so only the priority changes.
weights = ones(size(values));
spread = std(values, 1, 1);
spread(spread == 0) = 1;
names = unique(groups);
for g = 1:numel(names)
    members = strcmp(groups, names{g});
    if all(members)
        continue
    end
    lead = (mean(values(members, :), 1) - mean(values(~members, :), 1)) ./ spread;
    lead(direction < 1) = 0;
    raw = 1 + max(lead, 0);
    weights(members, :) = repmat(raw / mean(raw), nnz(members), 1);
end
end

function out = complementarity_from_data(values, groups)
% One minus the absolute correlation between criteria, within each group.
centered = values;
if isempty(groups)
    groups = repmat({'*'}, 1, size(values, 1));
end
names = unique(groups);
for g = 1:numel(names)
    members = strcmp(groups, names{g});
    centered(members, :) = values(members, :) - repmat(mean(values(members, :), 1), nnz(members), 1);
end
state = warning('off', 'all');
correlation = corrcoef(centered);
warning(state);
correlation(isnan(correlation)) = 0;
out = 1 - abs(correlation);
end

function rule = build_rule(problem, kind, tau, set_size)
% Builds the rule 'mean' (thesis) or 'minimum' (criteria in pairs).
if ~(isscalar(tau) && isnumeric(tau) && isfinite(tau) && tau > 0)
    error('memga:badTau', '''Tau'' must be a single finite number greater than 0.');
end
payment = normalize_values(problem.values, problem.direction);
if ~isempty(problem.groups)
    payment = payment .* group_weights(problem.values, problem.groups, problem.direction);
end
comp = problem.complementarity;
if isempty(comp)
    comp = complementarity_from_data(problem.values, problem.groups);
end
weights = problem.weights;
n_crit = size(payment, 2);

if strcmp(kind, 'minimum')
    pairs = nchoosek(1:n_crit, 2);
    first = pairs(:, 1)';
    second = pairs(:, 2)';
    factor = (weights(first) + weights(second)) / 2 .* comp(sub2ind(size(comp), first, second));
    rule = struct('kind', 'minimum', 'payment', payment, 'first', first, 'second', second, ...
                  'factor', factor, 'membership', [], 'tau', tau, 'n_combos', numel(first));
    return
end

if isempty(set_size)
    error('memga:badSize', 'The "mean" rule needs the size of the set.');
end
if set_size < 2 || set_size > n_crit
    error('memga:badSize', 'With the "mean" rule, the set must have from 2 to %d alternatives, and %d was requested.', ...
          n_crit, set_size);
end
total = nchoosek(n_crit, set_size);
if total > 10000
    error('memga:tooManyGroups', ...
          ['The "mean" rule would have %d criteria groups per evaluation, above the limit of 10000. ' ...
           'Use fewer criteria, a smaller set or the "minimum" rule.'], total);
end
combos = nchoosek(1:n_crit, set_size);
n_groups = size(combos, 1);
factor = zeros(1, n_groups);
membership = zeros(n_crit, n_groups);
for g = 1:n_groups
    group = combos(g, :);
    pairs = nchoosek(group, 2);
    factor(g) = mean(weights(group)) * mean(comp(sub2ind(size(comp), pairs(:, 1), pairs(:, 2))));
    membership(group, g) = 1 / set_size;
end
rule = struct('kind', 'mean', 'payment', payment, 'first', [], 'second', [], ...
              'factor', factor, 'membership', membership, 'tau', tau, 'n_combos', n_groups);
end

function values = rule_values(rule, means)
% MEANS has one row per set and one column per criterion.
if strcmp(rule.kind, 'minimum')
    values = min(means(:, rule.first), means(:, rule.second));
else
    values = means * rule.membership;
end
values = values .* repmat(rule.factor, size(values, 1), 1);
end

function [score, tie] = rule_rate_means(rule, means)
values = rule_values(rule, means);
% Rounding keeps a value equal to tau from falling below it because of floating point.
passed = round(values * 1e12) / 1e12 >= rule.tau;
score = mean(passed, 2);
tie = mean(min(values, rule.tau), 2);
end

function rated = rule_rate(rule, team)
means = mean(rule.payment(team, :), 1);
[score, tie] = rule_rate_means(rule, means);
rated = struct('score', score, 'tie', tie, 'team', sort(team));
end
