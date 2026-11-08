function [score, tie] = memga_score(problem, team, varargin)
%MEMGA_SCORE Score a set of alternatives that you chose yourself.
%
%   score = MEMGA_SCORE(problem, team) scores the set TEAM, a cell array of
%   names, with the same rule used by MEMGA. The score is between 0 and 1.
%   The second output is the tie-breaker, the average of min(value, tau).
%
%   Name-value options: 'Rule' ('mean', default, or 'minimum') and 'Tau'
%   (default 0.24).
%
%   Example:
%     p = memga_load_example('small');
%     memga_score(p, {'A1', 'A3'})

options = struct('Rule', 'mean', 'Tau', 0.24);
options = memga_parse_options(options, varargin);
rule_name = lower(options.Rule);
if ~any(strcmp(rule_name, {'mean', 'minimum'}))
    error('memga:badRule', 'Unknown rule ''%s''. Use ''mean'' or ''minimum''.', rule_name);
end
if ischar(team)
    team = {team};
end
[found, index] = ismember(team, problem.alternatives);
if ~all(found) || numel(unique(index)) ~= numel(index) || isempty(index)
    error('memga:badTeam', 'The team must name different alternatives of the problem.');
end
rule = memga_rules('build', problem, rule_name, options.Tau, numel(index));
rated = memga_rules('rate', rule, index(:)');
score = rated.score;
tie = rated.tie;
end
