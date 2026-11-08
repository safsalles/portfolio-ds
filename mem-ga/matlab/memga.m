function result = memga(problem, set_size, varargin)
%MEMGA Select a set of alternatives with the Multiple Choice Method.
%
%   result = MEMGA(problem, size) finds the set of SIZE alternatives that
%   best complements itself. A set is scored by the share of criteria
%   combinations in which it reaches the cutoff tau, so a set whose members
%   are strong in the same criteria scores below a set whose members cover
%   each other's weak points.
%
%   PROBLEM comes from MEMGA_PROBLEM, MEMGA_READ_PROBLEM or
%   MEMGA_LOAD_EXAMPLE. SIZE can be [] when 'Quotas' is given.
%
%   Name-value options:
%     'Method'   'exhaustive' (default) tests every combination and returns
%                the full ranking; 'ga' uses a genetic algorithm, for
%                problems too large to enumerate. It does not guarantee the
%                best answer, so repeat it with other seeds.
%     'Rule'     'mean' is the rule of the thesis that proposed the method:
%                criteria are combined SIZE at a time. 'minimum' is an
%                adaptation: criteria are combined two at a time and the
%                weaker of the two counts. Default: 'mean' with the
%                exhaustive search and 'minimum' with the genetic algorithm.
%     'Tau'      the cutoff, a number greater than 0 (default 0.24).
%     'Quotas'   vacancies per group, as a struct such as
%                struct('analyst', 2, 'manager', 1), or a cell array such as
%                {'analyst', 2; 'manager', 1}. Needs 'Groups' in the problem.
%     'Options'  settings of the genetic algorithm, from MEMGA_OPTIONS.
%     'Seed'     a seed to repeat a genetic algorithm result.
%     'Progress' true to show the progress of the genetic algorithm.
%
%   The result is a struct with the fields
%     team         names of the selected alternatives (the first set of the
%                  ranking, with the exhaustive search)
%     score        score of the team, between 0 and 1
%     ranking      exhaustive search only: position, set, score and members
%                  of every set tested
%     history      genetic algorithm only: best score at each iteration
%     traditional  the best alternatives one by one, and their score
%   Use MEMGA_PRINT(result) to show it and MEMGA_RADAR(result) to draw it.
%
%   Example:
%     result = memga(memga_load_example('small'), 2);
%     memga_print(result)
%
%   Reference: da Hora, H. R. M. and Costa, H. G. (2015). Proposta de um
%   metodo multicriterio para escolha multipla. Production, 25(2).
%   doi:10.1590/0103-6513.084812
%
%   See also MEMGA_PROBLEM, MEMGA_OPTIONS, MEMGA_SCORE, MEMGA_RADAR.

if nargin < 2
    set_size = [];
end
options = struct('Method', 'exhaustive', 'Rule', '', 'Tau', 0.24, 'Quotas', [], ...
                 'Options', memga_options(), 'Seed', [], 'Progress', false);
options = memga_parse_options(options, varargin);

method = lower(options.Method);
if ~any(strcmp(method, {'exhaustive', 'ga'}))
    error('memga:badMethod', 'Unknown method ''%s''. Use ''exhaustive'' or ''ga''.', method);
end
rule_name = lower(options.Rule);
if isempty(rule_name)
    if strcmp(method, 'exhaustive')
        rule_name = 'mean';
    else
        rule_name = 'minimum';
    end
end
if ~any(strcmp(rule_name, {'mean', 'minimum'}))
    error('memga:badRule', 'Unknown rule ''%s''. Use ''mean'' or ''minimum''.', rule_name);
end
tau = options.Tau;
ga_options = options.Options;
if ~isstruct(ga_options) || ~isfield(ga_options, 'iterations')
    error('memga:badOptions', '''Options'' must come from memga_options().');
end

quotas = memga_parse_quotas(options.Quotas, problem);
if isempty(set_size)
    if isempty(quotas)
        error('memga:badSize', 'Give the size, the number of alternatives to select.');
    end
    set_size = sum(quotas.counts);
elseif ~(isscalar(set_size) && set_size == round(set_size) && set_size >= 1)
    error('memga:badSize', 'The size must be a single whole number of at least 1.');
elseif ~isempty(quotas) && set_size ~= sum(quotas.counts)
    error('memga:badSize', 'The size is %d but the quotas add up to %d.', set_size, sum(quotas.counts));
end
n = size(problem.values, 1);
if set_size > n
    error('memga:badSize', 'The set asks for %d alternatives, but the data has only %d.', set_size, n);
end

rule = memga_rules('build', problem, rule_name, tau, set_size);

if ~isempty(options.Seed)
    cleanup = memga_seed(options.Seed); %#ok<NASGU>
end

traditional = memga_traditional(problem, set_size, quotas);
rated = memga_rules('rate', rule, find(ismember(problem.alternatives, traditional)));

result = struct('problem', problem, 'size', set_size, 'method', method, 'rule', rule_name, ...
                'tau', tau, 'quotas', quotas, 'seed', options.Seed, 'payment', rule.payment, ...
                'traditional', struct('team', {traditional}, 'score', rated.score));

if strcmp(method, 'exhaustive')
    found = memga_search('exhaustive', rule, n, set_size, problem.groups, quotas);
    n_sets = size(found.sets, 1);
    members = cell(n_sets, 1);
    labels = cell(n_sets, 1);
    for k = 1:n_sets
        members{k} = problem.alternatives(found.sets(k, :));
        labels{k} = strjoin(members{k}, ', ');
    end
    result.ranking = struct('position', found.position, 'set', {labels}, ...
                            'score', found.score, 'members', {members});
    result.team = members{1};
    result.score = found.score(1);
else
    found = memga_search('ga', rule, problem.groups, quotas, set_size, ga_options, options.Progress);
    result.team = problem.alternatives(found.team);
    result.score = found.score;
    result.history = found.history;
end

if result.score == 0
    warning('memga:noSetReachesTau', ...
            ['No set reaches tau (%g): the highest value found was %.3g. Try a smaller tau, ' ...
             'or give the complementarity matrix: computed from few alternatives, it tends to be near zero.'], ...
            tau, found.max_value);
end
end
