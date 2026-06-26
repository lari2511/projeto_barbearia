import React from 'react';

// Shim for @expo/vector-icons
export const createIconSet = () => () => null;

const Icon = ({ name, size = 16, color = 'currentColor', className, style }) => {
	return React.createElement('span', { className, style: { fontSize: size, color, ...style } }, name || 'icon');
};

export const MaterialCommunityIcons = Icon;
export const Ionicons = Icon;
export const FontAwesome = Icon;
export const Feather = Icon;

export default {
	createIconSet,
	MaterialCommunityIcons,
	Ionicons,
	FontAwesome,
	Feather
};
