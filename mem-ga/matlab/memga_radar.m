function memga_radar(result, varargin)
%MEMGA_RADAR Radar chart of the selected set.
%
%   MEMGA_RADAR(result) draws one axis per criterion and compares the
%   average performance of the selected set with the traditional choice and
%   with the average of all alternatives. A set that complements itself has
%   no deep dips: where one member is weak, another is strong.
%
%   Values are normalised performances, from 0 (worst) to 1 (best), so for
%   criteria in which less is better the axis is already inverted. When the
%   problem has groups they are adjusted by group, as in the score, so a
%   value can pass 1.
%
%   Option: 'Compare', false draws only the selected set (default true).

options = struct('Compare', true);
options = memga_parse_options(options, varargin);

payment = result.payment;
index = @(team) find(ismember(result.problem.alternatives, team));
profiles = {};
profiles(end + 1, :) = {'All alternatives', mean(payment, 1), [0.537 0.529 0.506], '--', false};
if options.Compare
    profiles(end + 1, :) = {'Traditional choice', mean(payment(index(result.traditional.team), :), 1), ...
                            [0.922 0.408 0.204], '-', false};
end
profiles(end + 1, :) = {'Selected set', mean(payment(index(result.team), :), 1), ...
                        [0.165 0.471 0.839], '-', true};

labels = result.problem.criteria;
count = numel(labels);
angles = pi / 2 - 2 * pi * (0:count - 1) / count;
top = max(1, ceil(max(cellfun(@max, profiles(:, 2))) * 2) / 2);

figure('Color', 'w');
hold on
axis equal off
circle = linspace(0, 2 * pi, 200);
for ring = 0.5:0.5:top
    plot(ring / top * cos(circle), ring / top * sin(circle), 'Color', [0.88 0.88 0.85]);
    text(0.02, ring / top, sprintf('%g', ring), 'FontSize', 7, 'Color', [0.54 0.53 0.51], ...
         'VerticalAlignment', 'bottom');
end
for k = 1:count
    plot([0 cos(angles(k))], [0 sin(angles(k))], 'Color', [0.88 0.88 0.85]);
    if abs(cos(angles(k))) < 0.15
        align = 'center';
    elseif cos(angles(k)) > 0
        align = 'left';
    else
        align = 'right';
    end
    text(1.17 * cos(angles(k)), 1.17 * sin(angles(k)), labels{k}, 'FontSize', 9, ...
         'HorizontalAlignment', align);
end

handles = zeros(1, size(profiles, 1));
for p = 1:size(profiles, 1)
    radius = profiles{p, 2} / top;
    px = radius .* cos(angles);
    py = radius .* sin(angles);
    if profiles{p, 5}
        fill(px, py, profiles{p, 3}, 'FaceAlpha', 0.18, 'EdgeColor', 'none');
    end
    handles(p) = plot([px px(1)], [py py(1)], profiles{p, 4}, 'Color', profiles{p, 3}, 'LineWidth', 2);
end
legend(handles, profiles(:, 1)', 'Location', 'southoutside', 'Orientation', 'horizontal');
title(sprintf('Selected set: %s (%.1f%%)', strjoin(result.team, ', '), 100 * result.score));
hold off
end
