import React from 'react';
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';

interface QuizProps {
	question: string;
	options: string[];
	correct_answer_index: number;
	explanation: string;
}

export const QuizSlide: React.FC<QuizProps> = ({
	question,
	options,
	correct_answer_index,
	explanation,
}) => {
	const frame = useCurrentFrame();
	const { fps, width, height } = useVideoConfig();

	// Timings (total ~10 seconds)
	// 0-1s: Intro animation
	// 1-6s: Question display + thinking time
	// 6s: Reveal correct answer
	// 6-10s: Explanation

	const opacity = spring({
		frame,
		fps,
		config: { damping: 20 },
	});

	const revealAnswer = frame > fps * 6;

	return (
		<AbsoluteFill
			style={{
				backgroundColor: '#050505',
				color: 'white',
				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				justifyContent: 'center',
				padding: '60px',
				fontFamily: 'Barlow Condensed',
				opacity,
			}}
		>
			<h2
				style={{
					fontSize: '70px',
					textAlign: 'center',
					marginBottom: '50px',
					color: '#FFD700',
					textTransform: 'uppercase',
				}}
			>
				Quick Quiz!
			</h2>

			<div
				style={{
					fontSize: '54px',
					textAlign: 'center',
					marginBottom: '80px',
					fontWeight: 'bold',
				}}
			>
				{question}
			</div>

			<div
				style={{
					display: 'flex',
					flexDirection: 'column',
					gap: '20px',
					width: '80%',
				}}
			>
				{options.map((option, index) => {
					const isCorrect = index === correct_answer_index;
					const highlight = revealAnswer && isCorrect;

					return (
						<div
							key={index}
							style={{
								fontSize: '40px',
								padding: '25px',
								borderRadius: '15px',
								backgroundColor: highlight ? '#2ECC71' : '#1A1A1A',
								border: highlight ? '4px solid #FFF' : '2px solid #333',
								transition: 'all 0.3s ease',
								display: 'flex',
								alignItems: 'center',
							}}
						>
							<span style={{ marginRight: '20px', color: '#888' }}>
								{String.fromCharCode(65 + index)}.
							</span>
							{option}
						</div>
					);
				})}
			</div>

			{revealAnswer && (
				<div
					style={{
						marginTop: '50px',
						fontSize: '32px',
						color: '#AAA',
						textAlign: 'center',
						fontStyle: 'italic',
					}}
				>
					{explanation}
				</div>
			)}

			{!revealAnswer && (
				<div
					style={{
						marginTop: '50px',
						height: '10px',
						width: '60%',
						backgroundColor: '#222',
						borderRadius: '5px',
						overflow: 'hidden',
					}}
				>
					<div
						style={{
							height: '100%',
							backgroundColor: '#FFD700',
							width: `${interpolate(frame, [fps, fps * 6], [0, 100], {
								extrapolateLeft: 'clamp',
								extrapolateRight: 'clamp',
							})}%`,
						}}
					/>
				</div>
			)}
		</AbsoluteFill>
	);
};
