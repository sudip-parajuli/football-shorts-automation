import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from 'remotion';

interface QuizProps {
	question: string;
	options: string[];
	correct_answer_index: number;
	explanation: string;
}

export const QuizSlide: React.FC<QuizProps> = ({ question, options }) => {
	const frame = useCurrentFrame();
	const { fps } = useVideoConfig();

	const opacity = spring({
		frame,
		fps,
		config: { damping: 20 },
	});

	// Stagger option entries
	const optionOpacity = (index: number) =>
		spring({ frame: frame - index * 6, fps, config: { damping: 18 } });

	return (
		<AbsoluteFill
			style={{
				backgroundColor: '#050505',
				color: 'white',
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				justifyContent: 'center',
				padding: '60px 100px',
				fontFamily: 'Barlow Condensed',
				opacity,
			}}
		>
			{/* Header */}
			<div
				style={{
					fontSize: '52px',
					textTransform: 'uppercase',
					letterSpacing: '8px',
					color: '#F5A623',
					fontWeight: 700,
					marginBottom: '20px',
				}}
			>
				⚽ Quick Quiz!
			</div>

			{/* Question */}
			<div
				style={{
					fontSize: '88px',
					fontWeight: 700,
					textAlign: 'center',
					marginBottom: '60px',
					lineHeight: 1.1,
					maxWidth: '1600px',
					textTransform: 'uppercase',
				}}
			>
				{question}
			</div>

			{/* Options */}
			<div
				style={{
					display: 'flex',
					flexDirection: 'column',
					gap: '24px',
					width: '85%',
				}}
			>
				{options.map((option, index) => (
					<div
						key={index}
						style={{
							fontSize: '60px',
							padding: '28px 40px',
							borderRadius: '18px',
							backgroundColor: '#1A1A1A',
							border: '2px solid #333',
							display: 'flex',
							alignItems: 'center',
							opacity: optionOpacity(index),
						}}
					>
						<span
							style={{
								marginRight: '24px',
								color: '#F5A623',
								fontWeight: 700,
								fontSize: '64px',
							}}
						>
							{String.fromCharCode(65 + index)}.
						</span>
						{option}
					</div>
				))}
			</div>

			{/* CTA */}
			<div
				style={{
					marginTop: '50px',
					fontSize: '44px',
					color: '#888',
					textAlign: 'center',
					fontStyle: 'italic',
				}}
			>
				💬 Drop your answer in the comments!
			</div>
		</AbsoluteFill>
	);
};
