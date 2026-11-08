function team = memga_traditional(problem, set_size, quotas)
%MEMGA_TRADITIONAL The traditional choice: the best alternatives one by one.
%
%   team = MEMGA_TRADITIONAL(problem, size) rates each alternative alone, by
%   the weighted average of its normalised performance, and keeps the best
%   SIZE. With quotas (see MEMGA_PARSE_QUOTAS), it keeps the best of each
%   group. MEMGA reports it next to the selected set for comparison.
%
%   Example:
%     memga_traditional(memga_load_example('small'), 2)

if nargin < 3
    quotas = [];
end
if isempty(set_size)
    set_size = sum(quotas.counts);
end
normalized = memga_rules('normalize', problem.values, problem.direction);
if sum(problem.weights) > 0
    strengths = normalized * problem.weights(:) / sum(problem.weights);
else
    strengths = sum(normalized, 2);
end
[~, order] = sort(-strengths);
order = order(:)';
if isempty(quotas)
    chosen = order(1:set_size);
else
    chosen = [];
    for g = 1:numel(quotas.names)
        inside = order(strcmp(problem.groups(order), quotas.names{g}));
        chosen = [chosen, inside(1:quotas.counts(g))]; %#ok<AGROW>
    end
end
team = problem.alternatives(chosen);
end
