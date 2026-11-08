function problem = memga_problem(values, varargin)
%MEMGA_PROBLEM Define a selection problem for the Multiple Choice Method.
%
%   problem = MEMGA_PROBLEM(values) describes how each alternative performs
%   on each criterion. VALUES is a numeric matrix with one row per
%   alternative and one column per criterion.
%
%   Name-value options:
%     'Alternatives'    cell array of names, one per alternative
%                       (default A1, A2, ...).
%     'Criteria'        cell array of names, one per criterion
%                       (default C1, C2, ...).
%     'Direction'       'max' (more is better, default) or 'min' (less is
%                       better), one for all or a cell array with one per
%                       criterion. Numeric 1 and 0 also work.
%     'Weights'         non-negative importance of each criterion, a scalar
%                       or one per criterion (default 1).
%     'Groups'          cell array with the group of each alternative, for
%                       example a job role. Criteria are then valued
%                       differently for each group, and 'Quotas' can be used
%                       in MEMGA.
%     'Complementarity' symmetric criteria-by-criteria matrix in which a
%                       higher value means that two criteria complement each
%                       other more. When omitted, it is computed from the
%                       data as one minus the absolute correlation between
%                       criteria, within each group when there are groups.
%
%   Example:
%     values = [9.5 9.0 6.2 2; 9.3 8.8 6.0 3; 6.4 7.0 9.4 4; 7.6 7.8 7.4 5];
%     p = memga_problem(values, 'Direction', {'max','max','max','min'});
%
%   See also MEMGA.

if ~isnumeric(values) || ~ismatrix(values)
    error('memga:badValues', '''values'' must be a numeric matrix.');
end
if any(~isfinite(values(:)))
    error('memga:badValues', '''values'' must not contain missing or infinite numbers.');
end
[n_alt, n_crit] = size(values);
if n_alt < 2 || n_crit < 2
    error('memga:badValues', 'The problem needs at least 2 alternatives and 2 criteria.');
end

options = struct('Alternatives', {{}}, 'Criteria', {{}}, 'Direction', 'max', ...
                 'Weights', 1, 'Groups', {{}}, 'Complementarity', []);
options = memga_parse_options(options, varargin);

alternatives = options.Alternatives;
if isempty(alternatives)
    alternatives = arrayfun(@(i) sprintf('A%d', i), 1:n_alt, 'UniformOutput', false);
end
criteria = options.Criteria;
if isempty(criteria)
    criteria = arrayfun(@(i) sprintf('C%d', i), 1:n_crit, 'UniformOutput', false);
end
alternatives = alternatives(:)';
criteria = criteria(:)';
if numel(alternatives) ~= n_alt || numel(criteria) ~= n_crit
    error('memga:badNames', 'Names must have one entry per alternative and per criterion.');
end
if numel(unique(alternatives)) ~= n_alt
    error('memga:badNames', 'The names of the alternatives must be unique.');
end

direction = memga_check_direction(options.Direction, n_crit);

weights = options.Weights;
if ~isnumeric(weights) || any(~isfinite(weights(:))) || any(weights(:) < 0)
    error('memga:badWeights', '''Weights'' must be finite numbers that are not negative.');
end
if ~any(numel(weights) == [1 n_crit])
    error('memga:badWeights', '''Weights'' must have length 1 or one value per criterion.');
end
weights = repmat(weights(:)', 1, n_crit / numel(weights));

groups = options.Groups;
if ~isempty(groups)
    if ~iscellstr(groups) || numel(groups) ~= n_alt
        error('memga:badGroups', '''Groups'' must be a cell array with one name per alternative.');
    end
    groups = groups(:)';
end

complementarity = options.Complementarity;
if ~isempty(complementarity)
    if ~isnumeric(complementarity) || ~isequal(size(complementarity), [n_crit n_crit]) ...
            || any(isnan(complementarity(:)))
        error('memga:badComplementarity', ...
              '''Complementarity'' must be a numeric matrix with one row and one column per criterion.');
    end
    complementarity(logical(eye(n_crit))) = 0;
end

constant = criteria(max(values, [], 1) == min(values, [], 1));
if ~isempty(constant)
    warning('memga:constantCriterion', ...
            'Criteria with the same value in every alternative do not tell the alternatives apart: %s.', ...
            strjoin(constant, ', '));
end

problem = struct('values', values, 'direction', direction, 'weights', weights, ...
                 'groups', {groups}, 'complementarity', complementarity, ...
                 'alternatives', {alternatives}, 'criteria', {criteria});
end
