function opts = memga_options(varargin)
%MEMGA_OPTIONS Settings of the genetic algorithm.
%
%   opts = MEMGA_OPTIONS() returns the defaults used in the original
%   implementation. Change one with a name-value pair, for example
%   memga_options('iterations', 2000). Names:
%     iterations         number of iterations (default 15000)
%     population         sets kept in the population (default 60)
%     stagnation         iterations without improvement before a mutation (14)
%     mutation_attempts  attempts in each mutation (7)
%     kick_size          alternatives swapped at once in the strong mutation (3)
%     climb_every        mutations between one strong mutation and the next (5)
%
%   Pass the result to MEMGA with the 'Options' option.

opts = struct('iterations', 15000, 'population', 60, 'stagnation', 14, ...
              'mutation_attempts', 7, 'kick_size', 3, 'climb_every', 5);
opts = memga_parse_options(opts, varargin);

values = [opts.iterations, opts.population, opts.stagnation, ...
          opts.mutation_attempts, opts.kick_size, opts.climb_every];
if ~isnumeric(values) || any(isnan(values)) || any(values ~= round(values))
    error('memga:badOptions', 'All settings of the genetic algorithm must be whole numbers.');
end
if opts.population < 2
    error('memga:badOptions', 'The population needs at least 2 sets.');
end
if min([opts.iterations, opts.stagnation, opts.mutation_attempts]) < 1
    error('memga:badOptions', 'iterations, stagnation and mutation_attempts must be at least 1.');
end
if min([opts.kick_size, opts.climb_every]) < 1
    error('memga:badOptions', 'kick_size and climb_every must be at least 1.');
end
end
