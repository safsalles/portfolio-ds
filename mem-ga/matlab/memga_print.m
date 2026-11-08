function memga_print(result, top)
%MEMGA_PRINT Show the result of MEMGA.
%
%   MEMGA_PRINT(result) prints the best sets (exhaustive search) or the
%   selected team (genetic algorithm) and the traditional choice.
%   MEMGA_PRINT(result, top) shows that many sets of the ranking (default 10).

if nargin < 2
    top = 10;
end
if strcmp(result.method, 'exhaustive')
    search = 'exhaustive search';
else
    search = 'genetic algorithm';
end
fprintf('Multiple Choice Method: %s, %s rule, tau %g\n', search, result.rule, result.tau);
fprintf('%d alternatives, %d criteria, selecting %d\n\n', ...
        numel(result.problem.alternatives), numel(result.problem.criteria), result.size);

if strcmp(result.method, 'exhaustive')
    ranking = result.ranking;
    fprintf('Best sets (%d tested):\n', numel(ranking.score));
    for k = 1:min(top, numel(ranking.score))
        fprintf('  %3d. %-24s %5.1f%%\n', ranking.position(k), ranking.set{k}, 100 * ranking.score(k));
    end
    if numel(ranking.score) > top
        fprintf('  ... %d more\n', numel(ranking.score) - top);
    end
else
    fprintf('Selected: %s (%.1f%%)\n', strjoin(result.team, ', '), 100 * result.score);
    if ~isempty(result.seed)
        fprintf('Seed: %d\n', result.seed);
    end
end

traditional = result.traditional;
fprintf('\nTraditional choice (best one by one): %s (%.1f%%)\n', ...
        strjoin(traditional.team, ', '), 100 * traditional.score);
if strcmp(result.method, 'exhaustive') && numel(traditional.team) == result.size
    for k = 1:numel(result.ranking.members)
        if isempty(setxor(result.ranking.members{k}, traditional.team))
            fprintf('It ranks %d in the Multiple Choice Method.\n', result.ranking.position(k));
            break
        end
    end
end
end
