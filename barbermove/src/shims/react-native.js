import React from 'react';

// Minimal shim for react-native used in web build
export const Platform = { OS: 'web', select: (obj) => obj.web || obj.default };

const passthrough = (tag) => (props) => {
	const { children, style, ...rest } = props || {};
	return React.createElement(tag, rest, children);
};

export const View = passthrough('div');
export const Text = passthrough('span');
export const Image = passthrough('img');
export const ScrollView = passthrough('div');
export const SafeAreaView = passthrough('div');
export const TouchableOpacity = passthrough('button');
export const TextInput = (props) => React.createElement('input', props);
export const ActivityIndicator = () => React.createElement('div', null, 'Loading...');
export const Alert = {
	alert: (title, message, buttons) => {
		try {
			console.log('[Alert]', title || '', message || '');
		} catch (_) {}
		return null;
	}
};
export const KeyboardAvoidingView = passthrough('div');
export const StyleSheet = {
	create: (styles) => styles
};

export default {
	Platform,
	View,
	Text,
	Image,
	ScrollView,
	SafeAreaView,
	TouchableOpacity,
	TextInput,
	ActivityIndicator
};
