function quotas = memga_parse_quotas(quotas, problem)
%MEMGA_PARSE_QUOTAS Internal. Turn the user's quotas into names and counts.
%   Accepts a struct (group names as field names) or an N-by-2 cell array.
%   Returns [] when there are no quotas.

if isempty(quotas)
    quotas = [];
    return
end
if isempty(problem.groups)
    error('memga:badQuotas', '''Quotas'' needs ''Groups'' in the problem.');
end
if isstruct(quotas)
    names = fieldnames(quotas)';
    counts = cellfun(@(name) quotas.(name), names);
elseif iscell(quotas) && size(quotas, 2) == 2
    names = quotas(:, 1)';
    counts = cell2mat(quotas(:, 2))';
else
    error('memga:badQuotas', '''Quotas'' must be a struct like struct(''analyst'', 2) or a cell array like {''analyst'', 2}.');
end
if any(isnan(counts)) || any(counts ~= round(counts)) || any(counts < 0)
    error('memga:badQuotas', '''Quotas'' must be whole numbers, zero or more.');
end
unknown = setdiff(names, problem.groups);
if ~isempty(unknown)
    error('memga:badQuotas', '''Quotas'' names groups that are not in the problem: %s.', strjoin(unknown, ', '));
end
keep = counts > 0;
if ~any(keep)
    error('memga:badQuotas', '''Quotas'' must ask for at least 1 alternative.');
end
quotas = struct('names', {names(keep)}, 'counts', counts(keep));
end
