function cleanup = memga_seed(seed)
%MEMGA_SEED Internal. Seed the random generator and restore it afterwards.
%   Keep the returned object in a variable: the generator is restored when
%   the variable goes out of scope.

if exist('rng', 'file') || exist('rng', 'builtin')
    previous = rng;
    rng(seed);
    cleanup = onCleanup(@() rng(previous));
else
    previous = rand('state'); %#ok<RAND>
    rand('twister', seed); %#ok<RAND>
    cleanup = onCleanup(@() rand('state', previous)); %#ok<RAND>
end
end
